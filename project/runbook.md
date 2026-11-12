# Runbook de produção (ADR 0011, 0024, 0025)

Estado: **a topologia e o ciclo backup → restauração só foram exercidos no CI**, nunca num servidor real nem com o tamanho real do banco. Monitoramento ainda não existe; não abra ao público antes dele e antes de **você mesmo restaurar um backup** (seção abaixo).

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

Para recuperar de um desastre **no banco em uso**: pare `web`, `agendador` e `backup` (`dc stop web agendador backup`), rode o mesmo comando com o banco `polis` e o último argumento `--substituir` (apaga o atual), e suba tudo de novo. Depois, reaplique as lápides da retirada pela fonte (ADR 0005) quando existirem.

## Não existe ainda
Monitoramento e alerta ativo (backup falho só aparece no healthcheck), domínio com certificado público, HSTS (`DJANGO_HSTS_SECONDS`), provedor do VPS e do armazenamento, medição do tempo de restauração com o tamanho real do banco (RTO de 24 h), lápides.
