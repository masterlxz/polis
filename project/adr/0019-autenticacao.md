# 0019: Autenticação: público anônimo, admin com senha e TOTP (P-09)

**Data:** 2026-11-08

## Contexto
O P-09 pede a estratégia de autenticação. O PRD pede conta de usuário só "caso necessário" (§6.11: acompanhar, alertas) e exige acesso administrativo controlado, com registro de ações (§11, §13). A Etapa 1 é leitura pública e a API do ADR 0013 é anônima: **nenhuma funcionalidade prevista usa conta pública**. O admin, ao contrário, enxerga campos internos (nome civil, data completa de nascimento, ADR 0005), então é a superfície sensível. Autenticação é área de risco (AGENTS.md §4): o dono confirmou o escopo (só admin agora) e o mecanismo (Django auth com TOTP obrigatório). Este ADR não implementa nada.

## Decisão
1. **Leitura pública anônima:** sem cadastro, sem login e sem cookie de identificação de visitante na Etapa 1 (privacidade, PRD §11).
2. **Só há contas de operador.** Autenticação do `django.contrib.auth` com senha forte e **TOTP obrigatório para todo operador**, sem exceção.
3. **Admin fora da superfície pública:** não fica aberto na mesma porta pública; acesso por rede restrita, VPN ou allowlist de IP no proxy. O mecanismo exato fica para a implantação (ADR 0011).
4. **Poucos operadores e privilégio mínimo** (grupos e permissões do Django). Campos internos do ADR 0005 só para quem precisar deles.
5. **Registro de ações administrativas** (PRD §11): quem, quando e o que mudou. Sem segredo nem campo interno nos logs.
6. **Recuperação:** códigos de recuperação do TOTP guardados fora do banco da aplicação; o segredo do TOTP nunca aparece em log nem em backup em claro.
7. **Sem criptografia própria:** senhas pelo hasher padrão do Django; TOTP (RFC 6238) por biblioteca estabelecida, a aprovar na implementação como dependência nova (AGENTS.md §4).
8. **Conta pública (alertas, acompanhar) e API com chave: adiadas.** Entram por ADR próprio quando uma funcionalidade exigir. Dado de usuário ficará separado do dado público (PRD §11) e passa pela validação do P-16.

## Alternativas
- **Senha sem 2FA:** mais simples, mas o admin vê dado interno sensível; descartada.
- **Login externo (OIDC ou GitHub):** delega identidade e MFA, mas acopla a um terceiro, contra o requisito self-hostable do ADR 0006; descartada.
- **Decidir conta pública agora:** nenhuma funcionalidade a usa e abriria questões de LGPD sobre dado de usuário sem necessidade; descartada.

## Consequências
- **Risco de ficar trancado fora:** com TOTP obrigatório e poucos operadores (talvez um só, ADR 0011), perder o aparelho sem códigos de recuperação bloqueia a administração. O runbook da implantação precisa cobrir isso.
- Proteger o admin por rede reduz a exposição a ataques de senha, mas o mecanismo escolhido na implantação é ponto de falha adicional.
- Uma biblioteca de TOTP entra como dependência de segurança e pede revisão própria e acompanhamento no Dependabot.
- A API com chave do ADR 0013 continua condicionada a ADR novo.
- **Não validado:** a biblioteca de TOTP, a configuração de rede do admin e o fluxo de recuperação de conta.
- **Fica aberto:** biblioteca, rede do admin, política de senha, níveis de permissão e conta pública.

## Nota de implementação (2026-11-08, Sessão 37)
- **Biblioteca escolhida:** `django-otp` 1.7.5 (dono aprovou a dependência). Descartada: `django-two-factor-auth` (mais dependências e última versão sem Django 6.x declarado). O admin passou a ser o `PolisAdminSite` (`config/admin.py`), que herda `OTPAdminSite`; o login exige senha, dispositivo e token, e o `has_permission` exige usuário verificado.
- **Divergência com a decisão 6 (lida no código da biblioteca, não presumida):** o `django-otp` guarda a chave do TOTP (`TOTPDevice.key`, hex) e os códigos estáticos de recuperação (`StaticToken.token`) **em texto no banco**. Portanto o segredo **fica em claro em qualquer backup do banco**. A biblioteca sozinha não cumpre "nunca em backup em claro". Mitigação exigida na implantação: backup cifrado (o ADR 0011 ainda não exige cifra) e acesso restrito ao banco. Isso fica pendente e deve virar requisito do runbook.
- **Limite de tentativas:** os dispositivos têm limitação exponencial de tentativas de token (ligada por padrão). Não há limite equivalente para a senha; a rede restrita do admin (decisão 3) continua sendo a defesa.
- **Fica aberto:** comandos `create_operator` e `reset_totp` com códigos de recuperação (PR seguinte), rede do admin, política de senha, permissões, cifra do backup e conta pública.
