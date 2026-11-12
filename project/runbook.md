# Runbook de produção (ADR 0011, 0024)

Estado: **a topologia só foi exercida no CI**, nunca num servidor real. Backup e monitoramento ainda não existem; não abra ao público antes deles.

Todos os comandos usam `docker compose -f compose.prod.yaml` (abaixo, `dc`). Atalho: `export COMPOSE_FILE=compose.prod.yaml`.

## Primeira subida
1. Copie `.env.example` para `.env` (nunca commite) e preencha `DJANGO_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) e `POSTGRES_PASSWORD`.
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
- `dc ps`: `db`, `web`, `front` e `agendador` devem estar `healthy`; `static` termina (`Exited 0`).
- `dc logs --tail=50 agendador`: uma linha por minuto de `collect_due` ("nada vencido" ou o que coletou). Erro de normalização aparece aqui e faz o comando sair com erro; o laço continua.

## Forçar uma coleta
No admin, ponha uma data passada em `next_collection_at` do conjunto; o agendador pega no minuto seguinte.

## Não existe ainda
Backup e teste de restauração (ADR 0011, decisão 3), monitoramento, domínio com certificado público, HSTS (`DJANGO_HSTS_SECONDS`), provedor do VPS.
