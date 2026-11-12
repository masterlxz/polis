# 0024: Compose de produção: fechado por padrão, proxy Caddy, agendador em laço

**Data:** 2026-11-12

## Contexto
O ADR 0011 fixou um VPS com Docker Compose e proxy reverso com TLS; o ADR 0023 deixou o disparo do `collect_due` a cada minuto para "fora do repositório". A Sessão 59 deixou o Django pronto para rodar atrás de proxy (`DJANGO_BEHIND_PROXY`, `DJANGO_HTTPS`, gunicorn). Faltava a topologia. Ainda não há servidor, domínio nem backup.

## Decisão
1. **Fechado por padrão.** `compose.prod.yaml` não publica 80 nem 443. O único `ports` é o do `caddy`, em `127.0.0.1:8443`, com `tls internal` (CA própria do Caddy); o acesso (site e admin) é por túnel SSH. Abrir ao público é ADR futuro (domínio, certificado público, HSTS, backup antes).
2. **`DJANGO_BEHIND_PROXY` só é seguro porque o `web` não publica porta**: só o Caddy o alcança, e o Caddy descarta `X-Forwarded-*` do cliente. O CI confere que só o `caddy` tem `ports`, e só em `127.0.0.1:8443`.
3. **A API interna não passa pelo proxy.** `/internal/*` devolve 404 no Caddy (ADR 0013: sem autenticação, isolada pela rede do Compose). O front a chama direto em `http://web:8000`.
4. **Roteamento:** `/admin/*` → Django; `/static/*` → arquivos no volume `static`; o resto → front (Next.js).
5. **Estáticos por volume, sem dependência nova** (descartado o `whitenoise`): o serviço `static` copia `/app/staticfiles` da imagem para o volume e termina; o Caddy o monta só para leitura. Roda como root só para escrever no volume recém-criado.
6. **Agendador = serviço `agendador`**, mesma imagem do `web`, rodando `scripts/agendador.sh`: `collect_due` a cada minuto alinhado ao começo do minuto (ADR 0023, decisão 1), erro do comando não derruba o laço, e um arquivo de batimento alimenta o healthcheck (vivo = volta concluída nos últimos 3 min).
7. **`migrate` é passo manual** do runbook, não serviço automático (migração é irreversível).
8. **Segredos** só pelo `.env`; sem `POSTGRES_PASSWORD` e `DJANGO_SECRET_KEY` o Compose recusa subir.
9. **CI:** job `producao` em `compose.yml` (não exigido no ruleset) prova a topologia com segredos descartáveis.

## Alternativas
- **Aberto com domínio desde já; nginx + certbot:** descartadas (decisão do dono na Sessão 59).
- **Cron do host para o agendador:** descartado; configuração fora do repositório e sem healthcheck.
- **`migrate` automático no `up`:** descartado; migra sem o dono olhar.
- **`whitenoise`:** descartado; dependência nova sem necessidade, o Caddy já serve arquivos.
- **Passar `/internal` ao Django com autenticação:** descartado; exigiria desenho de credencial que o ADR 0013 evita.

## Consequências
- **Batimento prova que o laço vive, não que a coleta funciona**: coleta falha segue visível só no admin e na saída do comando (ADR 0023); monitoramento é futuro.
- O laço não impede duas coletas se alguém rodar `ingest_dataset` junto; a reserva atômica do ADR 0023 cobre o agendador contra si mesmo.
- `tls internal` faz o navegador avisar de certificado desconhecido; aceitável por túnel.
- Estáticos antigos removidos de uma versão para outra permanecem no volume (`cp -a` só sobrescreve).
- **Não medido:** `WEB_CONCURRENCY=2`, memória da pilha inteira no VPS de ~US$ 20 (ADR 0011) e comportamento com HTTP/2 do Caddy sob carga.
- Backup (ADR 0011, decisão 3) e monitoramento continuam pendentes e bloqueiam a abertura ao público.
