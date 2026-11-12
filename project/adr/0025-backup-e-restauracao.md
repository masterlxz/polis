# 0025: Backup cifrado e restauração: pg_dump + age + S3 genérico

**Data:** 2026-11-12

## Contexto
O ADR 0011 (decisão 3) exige backup diário, fora da máquina do banco, no Brasil e com restauração testada; o ADR 0010 fixa RPO e RTO de 24 h. O ADR 0019 registrou que o `django-otp` guarda a chave do TOTP e os códigos de recuperação **em texto no banco**, então qualquer backup em claro vaza o segundo fator. Ainda não há provedor de armazenamento escolhido.

## Decisão
1. **Pipeline:** `pg_dump --format=custom` → `age` com **chave pública** → `rclone rcat` para um armazenamento S3-compatível, em `<bucket>/polis/AAAA-MM-DDTHHMMSSZ.dump.age`. O envio vai para um nome `.parcial` e só vira `.dump.age` no fim (um dump cortado nunca parece válido).
2. **Chave pública no servidor, privada com o dono.** O servidor só tem `BACKUP_AGE_RECIPIENTS` (uma ou mais chaves `age1...`); invadir o servidor não abre backups antigos. A chave privada nunca é montada no servidor em operação: entra por arquivo só na hora de restaurar. Recomendação de operação: **duas** chaves (a do dono e uma de recuperação guardada offline).
3. **S3-compatível genérico**, por variáveis de ambiente (`BACKUP_S3_ENDPOINT`, `_BUCKET`, `_ACCESS_KEY`, `_SECRET_KEY`), sem recurso exclusivo de provedor (ADR 0011, decisão 6). Provedor e região no Brasil seguem para a implantação.
4. **Agendamento:** serviço `backup` no Compose, laço diário às **03:17 UTC** (minuto não redondo, por analogia ao ADR 0008). Erro do comando não derruba o laço. O **batimento só é renovado depois de um backup bem-sucedido**; o healthcheck acusa quando passam 26 h sem sucesso.
5. **Retenção:** 14 dias, por **data no nome do objeto** (não pelo mtime), só em `polis/`, só nomes no formato exato, só depois de um envio bem-sucedido. Configurável em `BACKUP_RETENCAO_DIAS`.
6. **Restauração (`scripts/restaurar.sh`):** decifra **antes** de tocar em qualquer banco (chave errada ou objeto corrompido não deixam rastro); restaura num banco indicado; **recusa** um banco que já existe sem `--substituir`; se criou o banco e a restauração falhou, apaga o banco incompleto.
7. **Imagem própria (`Dockerfile.backup`):** base `postgres:18` (mesma versão do servidor para `pg_dump`/`pg_restore`), `rclone` copiado da imagem oficial `rclone/rclone` com tag fixa, `age` do Debian; roda como usuário `postgres`.
8. **Prova no CI** (job `producao`, S3 descartável com `rclone serve s3`): objeto sem a assinatura `PGDMP` nem a marca em claro; chave errada recusada sem criar banco; restauração fiel com o banco em uso intacto; proteção contra sobrescrever; poda respeita retenção e prefixo; laço sobrevive a falha e só o sucesso renova o batimento. Mutações pegas: sem cifra, poda fora do prefixo, restaurar sem exigir `--substituir`.

## Alternativas
- **restic:** descartado; a senha do repositório precisaria estar no servidor para gravar, então invadir o servidor exporia os backups.
- **Segundo servidor por SSH/rsync:** descartado; custo e operação de uma segunda máquina dentro do teto do ADR 0011.
- **`pg_dumpall`:** descartado; inclui papéis e é desnecessário para um banco só.
- **Cron do host:** descartado; configuração fora do repositório e sem healthcheck.
- **Backup em claro com bucket "privado":** descartado pelo ADR 0019.
- **`rclone` do Debian:** descartado; versão antiga (sem `serve s3`, necessário ao CI).

## Consequências
- **Perder todas as chaves privadas = perder todos os backups.** Sem recuperação possível.
- A credencial S3 do servidor consegue gravar e, no desenho atual, também apagar (a poda): recomenda-se credencial **só de escrita** mais regra de ciclo de vida do provedor para a retenção. **Não verificado**, depende do provedor.
- O dump em claro existe momentaneamente em `/tmp` do contêiner durante a restauração (apagado ao sair).
- **Não testado:** restauração em escala real (tamanho do banco desconhecido; 100 milhões de linhas é estimativa), então o RTO de 24 h **não foi medido**; um backup que falha avisa só pelo healthcheck (não há alerta ativo; monitoramento é futuro).
- A restauração **não** reaplica as lápides da retirada pela fonte (ADR 0005); a tabela ainda não existe, e o script avisa disso na saída.
- Cada backup e cada restauração tocam dados pessoais (ADR 0005, P-16): destino no Brasil enquanto não houver parecer.
- Bloqueia a abertura ao público até: provedor escolhido, **um teste de restauração real feito pelo dono**, chaves guardadas.
