# Runbook de produção (ADR 0011, 0024, 0025)

Estado: **a topologia e o ciclo backup → restauração só foram exercidos no CI**, nunca num servidor real nem com o tamanho real do banco. O monitoramento é só um painel: a lista de "Conjuntos de dados" do admin mostra a situação de cada fonte (em dia, atrasado, última coleta falhou, normalização falhou, sem agenda, desabilitado; atrasado = mais de 2 intervalos sem coleta com sucesso; "normalização falhou" = o bruto está fresco mas a normalização foi recusada ou falhou, e a mensagem aparece na coluna "última normalização"). O alerta ativo das fontes (seção "Alerta ativo") avisa por webhook quando uma fonte entra em atrasado, coleta falhou ou normalização falhou, mas **não cobre o backup nem o servidor inteiro cair**. Não abra ao público antes de **você mesmo restaurar um backup** (seção abaixo) e de ter um aviso para o backup e para o servidor caído.

Todos os comandos usam `docker compose -f compose.prod.yaml` (abaixo, `dc`). Atalho: `export COMPOSE_FILE=compose.prod.yaml`.

## Primeira subida
1. Copie `.env.example` para `.env` (nunca commite) e preencha `DJANGO_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) e `POSTGRES_PASSWORD`. Preencha também as `BACKUP_*` (seção "Chaves do backup" abaixo): sem elas o Compose recusa subir.
2. `dc up -d --wait db`
3. `dc run --rm web python manage.py migrate --noinput` (passo manual: migração é irreversível; leia o que será aplicado antes com `... migrate --plan`).
4. `dc run --rm web python manage.py seed_sources` (cadastro das fontes) e `create_operator` para o admin (TOTP obrigatório, ADR 0019).
5. `dc up -d --build --wait`

## Acesso (fechado por padrão)
Nada em 80/443. No seu computador: `ssh -L 8443:127.0.0.1:8443 usuario@servidor` e abra `https://localhost:8443/` (site) e `https://localhost:8443/admin/` (admin). O navegador avisa do certificado (CA interna do Caddy): esperado.

## Atualizar
1. `git pull` na `main`.
2. `dc build`
3. Se houver migração nova: `dc run --rm web python manage.py migrate --plan` e depois sem `--plan`.
4. `dc up -d --wait`

## Conferir saúde
- `dc ps`: `db`, `web`, `front`, `agendador` e `backup` devem estar `healthy`; `static` termina (`Exited 0`). `backup` fica `unhealthy` quando passam 26 h sem um backup bem-sucedido: olhe `dc logs backup`.
- `dc logs --tail=50 agendador`: uma linha por minuto de `collect_due` ("nada vencido" ou o que coletou). Erro de normalização aparece aqui e faz o comando sair com erro; o laço continua.

## Forçar uma coleta
No admin, ponha uma data passada em `next_collection_at` do conjunto; o agendador pega no minuto seguinte.

## Chaves do backup (fazer UMA vez, antes da primeira subida)
1. Gere **dois** pares de chaves `age`, no seu computador (ou `docker run --rm --entrypoint age-keygen polis-backup` depois de `dc build backup`): `age-keygen -o privada-1.txt` e `age-keygen -o privada-2.txt`. Cada comando imprime `Public key: age1...`.
2. Coloque as duas **públicas** em `BACKUP_AGE_RECIPIENTS`, separadas por vírgula.
3. Guarde `privada-1.txt` no seu gerenciador de senhas e `privada-2.txt` **offline, em outro lugar físico**. **Nenhuma privada vai para o servidor.** Perder todas = perder todos os backups, sem recuperação.
4. Para o armazenamento, use credencial só de **escrita** e configure no provedor a regra de ciclo de vida (o provedor ainda não foi escolhido).

## Backup
Automático: o serviço `backup` roda todo dia às 03:17 UTC e guarda 14 dias (`BACKUP_RETENCAO_DIAS`). Para rodar um agora: `dc run --rm backup bash scripts/backup.sh`. Para listar: `dc run --rm backup rclone lsf destino:$BACKUP_S3_BUCKET/polis/`.

## Restaurar (teste de restauração: faça o primeiro ANTES de abrir ao público)
Num banco **novo**, sem tocar no que está em uso:
```bash
dc run --rm -v /caminho/privada-1.txt:/chaves/privada.txt:ro -e AGE_IDENTITY=/chaves/privada.txt \
  backup bash scripts/restaurar.sh 2026-11-12T031700Z.dump.age polis_teste
```
Confira as contagens (`dc exec db psql -U polis -d polis_teste -c '...'`) e depois apague o banco de teste. O script decifra antes de criar qualquer banco e recusa um banco que já existe.

Para recuperar de um desastre **no banco em uso**: pare `web`, `agendador` e `backup` (`dc stop web agendador backup`), rode o mesmo comando com o banco `polis` e o último argumento `--substituir` (apaga o atual). **Antes de subir o `web`**, reaplique as lápides da retirada pela fonte (ADR 0005, 0026): `dc run --rm web python manage.py apply_tombstones` (idempotente; o backup pode trazer de volta dado que a fonte já retirou). Só então `dc up -d --wait`.

## Retiradas seguradas pelo disjuntor (ADR 0026)
Quando uma carga do TSE faz sumir mais que `max(20, 1%)` candidaturas, a normalização é recusada (`collect_due` sai com erro; o bruto fica; nada é apagado). Antes de liberar, **confira que o arquivo da fonte não está incompleto** (compare as contagens da última carga com a anterior no admin). Se a retirada é legítima: `dc run --rm web python manage.py normalize_tse --aceitar-retiradas`. **Apaga dado pessoal sem volta.** Um `--aceitar-retiradas` que dá certo limpa a coluna "última normalização" do admin, e o aviso de normalização deixa de valer (o alerta manda "RECUPERADO" na próxima passada, se a coleta não falhou). Se o comando recusar, a coluna continua com a recusa que o agendador gravou.

## Carga do TSE recusada por linha inválida ou conflito (não é o disjuntor)
**Como reconhecer:** o alerta "Normalização falhou" de `tse/consulta-cand-2026` termina com "Enquanto isso, nenhuma retirada pedida pela fonte é efetivada." A frase sai em **três** casos, que se distinguem pela mensagem entre parênteses (a mesma da coluna "última normalização" do admin):
- "linhas inválidas" ou "dados conflitantes entre linhas do bruto": **esta seção**.
- "candidaturas sumiram do arquivo": o disjuntor (`RetirementsHeld`); siga a seção "Retiradas seguradas pelo disjuntor", acima.
- "Falha inesperada na normalização": erro que não é recusa. O log do `agendador` (`dc logs agendador`) traz a linha "normalização falhou de forma inesperada (NomeDaClasse)": o nome da classe da exceção (uma classe de banco, como `IntegrityError` ou `OperationalError`, aponta para o banco; outra, para o código), **sem a mensagem**, de propósito: a mensagem de um erro do banco cita valores de linha. O `normalize_tse` também troca a causa pela mensagem genérica. Passo a passo: confira `dc ps` e o banco (`db` saudável, disco, conexões); rode `dc run --rm web python manage.py normalize_tse` uma vez (pode ter sido transitório); se persistir, reproduza num shell na máquina do dono sabendo que a mensagem do erro pode citar valores de linha.

Nos dois primeiros casos (linha inválida/conflito e disjuntor) a mensagem gravada é cortada em 300 caracteres; a completa sai de `dc run --rm web python manage.py normalize_tse` (sem rede; ao recusar não grava nem apaga nada).

**Quando a coleta também falhou:** a situação é "Última coleta falhou" (ela vence "Normalização falhou", `freshness.py`) e o aviso mostra o rótulo do erro da coleta, **sem** a mensagem da recusa. Se a recusa anterior ainda está aberta, o aviso termina com a mesma frase ("nenhuma retirada pedida pela fonte é efetivada") e as retiradas seguem paradas. Nesse caso **não espere a coleta**: a mensagem da recusa não vem no aviso, então leia já a coluna "última normalização" do admin e siga a seção que ela indica (linha inválida ou conflito: esta; "candidaturas sumiram do arquivo": a do disjuntor, cujo `normalize_tse --aceitar-retiradas` roda sem rede e destrava na hora; falha inesperada: o passo a passo do terceiro caso, acima). Só o caso de linha inválida ou conflito depende de um arquivo novo da fonte; o erro da coleta (entre parênteses) é um problema à parte. **Quando a frase é confiável:** um `normalize_tse` à mão que dá certo (por exemplo `--aceitar-retiradas`) efetiva as retiradas **e limpa** a "última normalização" (item 3 de "O que fazer"), então a frase some do aviso na próxima passada. Se ela ainda aparece, a última tentativa (do agendador ou à mão) foi uma recusa ou uma falha, e as retiradas seguem paradas: um `normalize_tse` que recusa ou falha não mexe na coluna.

**O que significa:** a normalização lê e valida a carga inteira (`_collect`) antes de gravar qualquer coisa (`_write`, que é quem aplica as retiradas). Uma linha inválida ou um conflito recusam tudo: nem candidatura nova nem retirada é efetivada, então o dado pessoal que a fonte tenha pedido para retirar **continua publicado** até a carga passar. Enquanto o bruto do dia estiver nesse estado, o agendador retenta a cada coleta bem-sucedida do conjunto (1 vez por dia, também quando o arquivo veio igual) e o alerta repete a cada 24 h.

**`--aceitar-retiradas` não destrava isto:** ele só liberta o disjuntor (`retirement.plan`), que roda depois da validação. `normalize_tse` à mão faz a mesma validação e recusa do mesmo jeito; não há atalho manual.

**O que fazer:**
1. Leia a mensagem (só nomes, tipos e contagens, nunca valores). Em "linhas inválidas" ela lista as **colunas** com a quantidade de linhas ruins (`colunas: NR_TURNO (3)`). Em "dados conflitantes" ela lista o **tipo do conflito** com a contagem (`eleições`, `pessoas`, `candidaturas`), sem coluna. Confira o arquivo da fonte no portal do TSE: formato mudou, coluna nova ou vazia, valor fora do esperado, cópias da mesma candidatura que divergem.
2. Se o arquivo está errado, espere a fonte publicar um corrigido: a coleta que o baixa já o normaliza (`scheduling._handle` chama `_normalize` depois de coleta bem-sucedida), sem passo manual. Para não esperar o dia, force a coleta (seção "Forçar uma coleta"). `normalize_tse` não ajuda aqui: ele lê a mesma carga mais recente e recusa igual.
3. Se o arquivo está certo e o parser é que não o aceita (`apps/elections/tse.py`), a correção é um PR no parser. Depois de implantado, `normalize_tse` à mão efetiva as retiradas paradas, com dois cuidados:
   - `normalize_tse` bem-sucedido **limpa** a "última normalização" do admin e grava a hora (recusa ou falha inesperada não mexem nela; os outros comandos `normalize_*`, da Câmara e do Senado, fazem o mesmo nos conjuntos que normalizam): o aviso ("Normalização falhou", ou "Última coleta falhou" com a frase, se a coleta também falhou) deixa de valer: se a coleta não falhou, o alerta manda "RECUPERADO" na próxima passada; se falhou, o aviso segue "Última coleta falhou", agora sem a frase. Se ele recusar de novo, a coluna continua com a recusa que o agendador gravou, e a mensagem nova sai só no terminal.
   - As retiradas acumuladas podem passar do disjuntor `max(20, 1%)` e a carga ser recusada de novo, agora com "candidaturas sumiram do arquivo". Nesse caso siga a seção do disjuntor, conferindo o arquivo antes de `--aceitar-retiradas`.

## Alerta ativo (Sessão 76)
O `collect_due` (rodado a cada minuto pelo `agendador`) avisa por webhook quando uma fonte **entra** em "Atrasado", "Última coleta falhou" ou "Normalização falhou", repete **1 vez por dia** enquanto continuar ruim e avisa a **recuperação**. Uma mensagem por volta, com todos os conjuntos que precisam de aviso.
1. Escolha um webhook que aceite **POST de texto puro** (por exemplo um tópico do ntfy, que pode ser auto-hospedado) e ponha a URL **https** em `ALERT_WEBHOOK_URL` no `.env`. A URL costuma carregar o segredo: trate como senha. Vazia, o alerta fica desligado; inválida (não https), o Django recusa subir.
2. `dc up -d agendador` para o serviço pegar a variável. Só o `agendador` a recebe.
3. Para testar (ainda **não exercido** num servidor real): aponte um conjunto para uma URL inválida no admin, force a coleta (seção "Forçar uma coleta"), espere uma volta e veja o aviso chegar; depois restaure a URL e veja o "RECUPERADO".
A mensagem leva só `fonte/conjunto`, a situação e o código de erro ou a mensagem da recusa (só colunas e contagens). Se o webhook estiver fora do ar, o aviso **não se perde**: o estado só é gravado depois de o envio dar certo e a volta seguinte tenta de novo (uma requisição por minuto).
**O que este alerta não vê:** backup que falhou (só o healthcheck do contêiner), e o servidor, o Docker ou o próprio agendador parados (ninguém roda o envio). Para o servidor caído é preciso um serviço **externo** que espere um batimento e avise quando ele parar (*dead man's switch*).

## Não existe ainda
Alerta do backup e do servidor caído (o alerta ativo só cobre as fontes; o erro de normalização só é visto do agendador, não da normalização manual `normalize_*`), domínio com certificado público, HSTS (`DJANGO_HSTS_SECONDS`), provedor do VPS e do armazenamento, medição do tempo de restauração com o tamanho real do banco (RTO de 24 h), lápide para o deputado da Câmara (ADR 0026).
