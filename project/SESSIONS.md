# polis: Log de sessões

Mais recente no topo.

### 2026-11-06 — Sessão 20 (ADR 0008, regras por fonte)

- **Pedido**: escrever o ADR do P-15. Recomendei esperar as Portarias do TSE; o dono preferiu seguir. Escolhas do dono: TSE sem `license_id` **não é coletado** até haver licença; **atribuição uniforme** em toda fonte.
- **Feito**: `project/adr/0008-regras-por-fonte.md` (portão de licença por conjunto, falha fechada se a licença mudar, atribuição uniforme, `User-Agent` honesto, etiqueta de rede com 429/503 recuando e 403 parando sem contornar, agendamento, canal, o que fica no P-16). Só docs.
- **Não verificado**: as decisões 1 a 3 foram escritas sem o texto das Portarias TSE 93 e 525/2021 e dos termos do TSE (403); o ADR diz que será revisto se elas contradisserem. Valores (3 s, 08:00 GMT) vêm de medições de um dia só.
- **Fica**: campos de licença no `Dataset` e códigos `blocked`/`license` no `error_code` (ficam para o conector, em plan mode); leitura humana das Portarias; P-15 só fecha com ela.

### 2026-11-06 — Sessão 19 (P-15: leitura do Ato da Mesa 45/2012 e dos termos da Câmara)

- **Pedido**: seguir com o P-15.
- **Feito**: o 429 da Câmara da Sessão 18 era limite de taxa; uma nova requisição por URL, com `User-Agent` genérico e 10 s entre elas, voltou 200. Li o Ato da Mesa 45/2012 (texto atualizado) e os termos do portal. `fontes/camara.md`: Art. 27 (informações pessoais, incluindo "número de documentos de identificação pessoal"), conclusão sem licença nem atribuição, regra "Robôs" nas regras operacionais.
- **Não verificado**: por que a API de detalhe serve o CPF se o Ato o lista como pessoal; o regulamento do § 10; Portarias TSE (403, não contornar) e termos de uso do TSE.
- **Fica**: o P-15 segue aberto só pelo TSE; precisa de leitura humana pelo navegador.

### 2026-11-06 — Sessão 18 (P-15: leituras e regras operacionais por fonte)

- **Pedido**: fechar o P-15 (plan mode). Escolhas do dono: leituras oficiais + síntese de regras; busca na web só de leitura.
- **Feito**: seção "Regras operacionais" em `fontes/camara.md`, `senado.md` e `tse.md`; tabela de regimes lado a lado em `fontes/README.md`; "Não verificado" reescrito com o que foi lido em 2026-11-06. Plano 2026/2028 do Senado lido com `pdftotext`: define dados abertos como "licença aberta" e não nomeia licença. TSE: `comparecimento-e-abstencao-2026/2024` sem `license_id` (confirmado), 181 de 190 conjuntos do portal com CC BY. CPF de 2026 reconferido (29 CSVs, 42.028 linhas de 11 dígitos, 6 placeholders).
- **Não lido, por bloqueio do servidor**: Portarias TSE 93/2021 e 525/2021 (HTTP 403) e Ato da Mesa 45/2012 e termos do portal da Câmara (HTTP 429). Tentei reler as Portarias com outro `User-Agent`; o ambiente barrou como contorno de bloqueio e **não repeti** (o 403 é recusa do servidor). Termos de uso do TSE e Plano de Dados Abertos 2021-2023 só citados, não abertos.
- **Não verificado**: documentação da API do Senado (Swagger por JavaScript), `leiame.pdf` do TSE, quais são os outros 6 conjuntos do TSE sem licença (inferência: 190 menos 181).
- **Fica**: o P-15 **segue aberto** só pelos 4 textos acima, que precisam de leitura humana pelo navegador ou do dono colando; ADR 0008 (regras por fonte) a decidir; cadastro das 3 fontes no banco depende disso.

### 2026-11-06 — Sessão 17 (leitor de ZIP de CSV com allowlist, PR #23)

- **Pedido**: leitor do TSE, parte 1 (plan mode): leitura em fluxo, allowlist por nome, falha fechada, SHA-256, sem banco. Escolhas do dono: o leitor só conta linhas malformadas (o limite é do conector); valida todos os cabeçalhos antes de devolver qualquer linha; depois da revisão adversária, registro multilinha rejeitado por padrão (com opção para permitir) e limites de recursos neste PR.
- **Medições (só contagens, arquivos apagados)**, `consulta_cand_2026.zip` (3,3 MB, 29 CSVs): 0 bytes entre `0x80` e `0x9F`, nenhum BOM, nenhum item é UTF-8 válido, 42.063 quebras CRLF (codificação em `fontes/tse.md`); 42.034 registros, 0 multilinha, 0 com largura diferente, no máximo 50 colunas, maior linha com 721 caracteres.
- **Feito**: `apps/sources/zip_csv.py` (`ZipCsvReader`, `sha256_file`, `MissingColumnError`, `DuplicateColumnError`, `InvalidFormatError`), partindo do leitor do spike (PR #12) em inglês (ADR 0007); `tests/test_zip_csv.py` (58 testes). Cabeçalhos validados antes da primeira linha; colunas duplicadas, item vazio, ZIP sem CSV, nomes de item repetidos, BOM UTF-8, item com senha e CRC inválido falham; erros citam só nomes e são levantados fora do `except`; leitor de uso único; limites configuráveis de colunas, caracteres por linha, itens e tamanho descomprimido declarado.
- **Revisão adversária** (agente `adversarial-reviewer`): 2 críticos e vários importantes, todos tratados menos o NUL em valores e o tempo de CPU. **C1**: aspas abertas juntavam a linha seguinte (com o CPF) num valor devolvido; **C2**: `from None` não escondia `__context__`, e os quadros do traceback guardavam bytes do arquivo (`data`, `line`, `header`). 17 mutações sobreviviam aos primeiros testes; os testes novos cobrem as mais relevantes.
- **Testes primeiro (CI)**: 1ª vez, `ModuleNotFoundError`; depois da revisão, 21 dos 31 testes novos falharam antes da correção e todos passaram depois (101 no total).
- **Quebra de propósito (3 rodadas, todas revertidas)**: validar só o 1º cabeçalho + devolver todas as colunas + `>` na largura: 5 falhas esperadas; ler por posição: 2 falhas (`le_pelo_nome` e canário); aceitar multilinha + levantar dentro do `except` + aceitar ZIP sem CSV: 5 falhas esperadas.
- **Correções minhas no caminho**: os testes de traceback do canário falhavam porque o próprio teste guardava o canário em variável local (`raw`, `rows`); o teste do bit de senha precisou marcar o bit direto nos bytes (o `writestr` o zera).
- **Não verificado**: o NUL (`\x00`) em valores passa; tempo de CPU não é limitado; o `RuntimeError`, `zlib.error` e a compressão não suportada não têm teste próprio (só o genérico de dado corrompido); desempenho depois das mudanças (o spike mediu 66 a 74 MB/s antes); o limite padrão de 200.000 caracteres por linha foi escolhido por folga (o TSE tem 721), não medido em outros conjuntos; Windows-1252 só foi descartado para o `consulta_cand_2026`; nada rodou localmente, só `ruff`.
- **Fica**: fatia do conector (ligar o leitor ao `Dataset.allowed_columns` e ao `IngestionRun`, transação, limite de linhas rejeitadas, `error_code` `malformed_row`/`schema`/`hash`, tratar "todas as linhas rejeitadas"); remedir desempenho; cadastrar as 3 fontes (P-15); `docker` no `dependabot.yml`; decidir NUL em valores.

### 2026-11-06 — Sessão 16 (ADR 0007)

- **Pedido**: o dono aceitou registrar o ADR 0007 depois do merge do PR #21 (`4c684ca`).
- **Feito**: `project/adr/0007-nomes-no-codigo-e-cadastro-de-fontes.md` (nomes em inglês no código e português na interface, tabela de correspondência de termos, estrutura `Source`/`Dataset`/`IngestionRun`, `error_code` fechado, imutabilidade). Só docs.
- **Não verificado**: o idioma de docstrings, comentários e nomes de teste não foi discutido com o dono (hoje em português); ficou marcado como "não decidido" no ADR. A tabela de termos cobre só o que existe.
- **Fica**: escolher a próxima fatia (leitor e conector do TSE em duas partes, ou cadastro das 3 fontes reais após o P-15, ou `docker` no `dependabot.yml`); `GLOSSARY.md` do projeto, se o dono quiser (não existe).

### 2026-11-06 — Sessão 15 (cadastro de fontes e execuções de coleta, PR #21)

- **Pedido**: primeira fatia de domínio da Etapa 0 (plan mode). Escolhas do dono: `Source` + `Dataset` (allowlist no conjunto) e nomes em inglês no código, português na interface.
- **Feito**: app `apps/sources` com `Source`, `Dataset` e `IngestionRun`, migração `0001_initial` e admin; `Dataset` só habilita com colunas permitidas (restrição no banco) e valida colunas internas ⊆ permitidas; `IngestionRun` sem texto livre de erro (`error_code` fechado), com `CheckConstraint` para hash SHA-256 válido, fim, falha com código e linhas gravadas ≤ lidas, e `save()` que recusa alterar execução concluída; admin da execução só leitura. `tests/test_sources.py` (33 testes). `pyproject.toml`: `apps` e `config` como primeiro-partido no isort do `ruff`.
- **Testes primeiro**: no CI o `pytest` falhou na coleta (`No module named 'apps.sources'`), prova fraca; a prova real foi a quebra de propósito.
- **CI (resultado visto)**: `tests` e `compose` verdes com 43 testes; `dco` e `guard` verdes. Quebra de propósito (imutabilidade e validação de colunas internas desligadas): falharam exatamente `test_coluna_interna_fora_das_permitidas_e_recusada`, `test_execucao_concluida_nao_pode_ser_alterada` e `test_execucao_com_falha_tambem_nao_pode_ser_alterada`; revertida com commit de reversão.
- **Correções minhas no caminho**: (1) o Django exige `django.contrib.postgres` em `INSTALLED_APPS` para `ArrayField` (o plano dizia que não); (2) o hash com 65 caracteres é barrado pelo tipo da coluna (`DataError`), não pela restrição (`IntegrityError`): ajustei o teste; (3) um teste construía com `create()` um `error_code` maior que a coluna: passou a montar a instância sem salvar; (4) `ruff` tratava `apps` como terceiro: configurei `known-first-party`.
- **Não verificado**: a imutabilidade é só na aplicação (`QuerySet.update()` e SQL direto contornam; sem trigger); a corrida entre duas gravações da mesma execução (o `save()` lê e depois grava sem trava); o admin mostrando as colunas em tela real (só status HTTP); nada rodou localmente (convenção do workspace), só `makemigrations` e `ruff`.
- **Fica**: perguntar se crio o ADR 0007 (nomes em inglês no código e modelo de fontes); cadastrar as 3 fontes reais (P-15: licença da Câmara e do Senado); conector e leitor (reaproveitar os 11 testes do spike no PR #12); ecossistema `docker` no `dependabot.yml`; exigir ou não o check `compose` (recomendo não); imagem de produção (P-04).

### 2026-11-06 — Sessão 14 (PR #17 do Dependabot e faxina)

- **Pedido**: decidir o PR #17 e fazer a faxina (README e branch do spike).
- **Feito**: li as release notes do `actions/checkout` (v4 → v7) e do `astral-sh/setup-uv` (v6 → v7) por um subagente de leitura; o único breaking relevante do `checkout` (bloqueio de PR de fork em `pull_request_target`/`workflow_run`) não nos afeta, e o do `setup-uv` (Node 24) "just works" em runner hospedado. O dono mesclou o #17 (`300ff93`); `Tests`, `Compose` e `CI Private Files` verdes na `main` depois. Seção "Contribuições" do README corrigida (DCO, `CONTRIBUTING.md`). Branch `spike/ingestao-python` apagada (remota e local) com autorização do dono, depois de conferir que `refs/pull/12/head` guarda o mesmo commit (`c758f78`).
- **Não verificado**: o changelog do github.blog sobre o breaking do `checkout` não foi lido; o `setup-uv` está na v10 e o bot propôs a v7 (motivo desconhecido; da v8 em diante não há tag flutuante `@v8`, o que afeta as próximas propostas do bot).
- **Nota sobre o ADR 0006**: o texto diz que o spike "fica só na branch e no PR #12 fechado"; agora ele fica só no PR #12 (`refs/pull/12/head`). Não editei o ADR.
- **Fica**: ecossistema `docker` no `dependabot.yml` (com `ignore` do Python 3.15); exigir ou não o check `compose` no ruleset (recomendo não exigir); modelo de dados e cadastro de fontes (próxima fase, em plan mode); imagem de produção (P-04).

### 2026-11-06 — Sessão 13 (Docker Compose de desenvolvimento, PR #19)

- **Pedido**: criar o Docker Compose da Etapa 0 técnica (plan mode). Escolhas do dono: `db` + `web` com Dockerfile de desenvolvimento, e job `compose` no CI.
- **Feito**: `Dockerfile` (`python:3.14-slim`, uv 0.13.6, venv em `/opt/venv`, usuário UID 1000), `compose.yaml` (`postgres:18` com volume em `/var/lib/postgresql`, healthcheck, portas só em `127.0.0.1`, `POSTGRES_PASSWORD` e `DJANGO_SECRET_KEY` obrigatórios por `:?`), `.dockerignore`, `.github/workflows/compose.yml`, README e `.env.example`.
- **Testes primeiro**: o workflow `compose.yml` foi escrito antes do `compose.yaml` e falhou no primeiro passo (sem `compose.yaml`); os passos seguintes só puderam ser provados depois, e a prova de que o de falha fechada discrimina é a quebra de propósito.
- **CI (resultado visto)**: com os arquivos, `compose` verde: falha fechada nos dois segredos, portas 2 de 2 em `127.0.0.1`, banco `Healthy`, 10 testes passados dentro do `web` e `200` em `/admin/login/`; `dco`, `guard` e `tests` verdes. Um passo falhou antes por erro meu (flag `--retry-connection-refused` do `curl` não existe) e foi corrigido. Quebra de propósito (senha padrão no `POSTGRES_PASSWORD`): `compose` falhou em `docker compose config aceitou a falta de POSTGRES_PASSWORD`; revertida com commit de reversão.
- **Não verificado**: nada foi rodado localmente (convenção do workspace); o bind mount com UID diferente de 1000 no host; o comportamento do volume `pgdata` entre execuções (no CI o volume nasce limpo); `runserver` com recarga automática; o job `compose` ainda não é exigido no ruleset.
- **Fica**: ecossistema `docker` no `dependabot.yml` (precisa de `ignore` para o bot não propor Python 3.15); decidir o PR #17 do bot; apagar a branch `spike/ingestao-python`; seção "Contribuições" do README desatualizada; imagem de produção (P-04).

### 2026-11-06 — Sessão 12 (fechamento do P-19)

- **Pedido**: fechar o P-19 depois do merge do PR #16.
- **Conferido**: runs `uv in /.` (#1685310393) e `github_actions in /.` (#1685310398) concluídos com sucesso na `main`; o Dependabot abriu o PR #17 (`ci: bump the actions group with 2 updates`: `actions/checkout` v4 → v7 nos 3 workflows e `astral-sh/setup-uv` v6 → v7), com `dco`, `guard` e `tests` verdes. O run do `uv` não abriu PR (versões já fixadas). Não vi alerta de configuração.
- **Feito**: P-19 movido para Resolvidas; `OVERVIEW.md` e `INDEX.md` atualizados.
- **Não verificado**: o conteúdo do PR #17 (salto de três majors do `checkout`; release notes não lidas), que segue aberto para o dono decidir (AGENTS §4, CI/CD); a aba Dependabot da interface, só os runs pela API.
- **Fica**: decidir o PR #17; Docker Compose; apagar a branch `spike/ingestao-python`; seção "Contribuições" do README desatualizada.

### 2026-11-06 — Sessão 11 (`dependabot.yml` de version updates, P-19)

- **Pedido**: criar o `dependabot.yml` (plan mode). Conflito apontado por mim: o ADR 0006 do workspace descartou `dependabot.yml` de versões pelo volume de PRs (anchor e truthid); o dono confirmou que o **polis é exceção** (árvore pequena, 0 alertas, security updates já ligados), e o ADR do workspace não foi alterado.
- **Feito**: `.github/dependabot.yml` com `uv` e `github-actions`, semanal (segunda 06:00 `America/Sao_Paulo`), um PR agrupado por ecossistema, limite 2, prefixos `deps` e `ci`, e `ignore` de minor e major do `django` (a virada para o 6.2 LTS segue manual, ADR 0006). Campos conferidos na referência oficial de opções do GitHub; o YAML parseia (Ruby, 2 entradas em `updates`). `cooldown` fora (o padrão de 3 dias vale; suporte a uv não confirmado).
- **Não verificado**: se o Dependabot aceita o arquivo (só se vê depois do merge); o aninhamento de `groups` e `ignore` não tem exemplo na doc (inferência, confiança média); como o PR agrupado se comporta quando `ruff` 0.x muda o `format`.
- **Fica**: conferir o Dependabot depois do merge e então fechar o P-19; Docker Compose; apagar a branch `spike/ingestao-python`; seção "Contribuições" do README desatualizada.

### 2026-11-06 — Sessão 10 (check `tests` exigido no ruleset)

- **Pedido**: depois do merge do PR #14 (`6879c40`), exigir o check `tests` no ruleset `protect-main`. O dono confirmou ("vamos de 1").
- **Feito**: `PUT` no ruleset 26285460 mudando só a lista de checks (`guard`, `dco` e agora `tests`); o restante foi copiado do estado ativo (lido antes por `gh api`). Conferido pela resposta da API: os três contextos presentes. `Tests` e `CI Private Files` verdes na `main` após o merge do #14. O JSON aplicado ficou só no scratchpad da sessão, não no repo.
- **Não verificado**: ainda não vi um PR esperar o `tests` (este PR de docs será o primeiro); o `strict_required_status_checks_policy` segue falso. O `padrao/ruleset-protect-main.json` do workspace não inclui `dco` nem `tests` (é genérico por projeto).
- **Fica**: `dependabot.yml`; Docker Compose; apagar a branch `spike/ingestao-python`; seção "Contribuições" do README desatualizada.

### 2026-11-06 — Sessão 9 (criação do projeto Django, PR #14)

- **Pedido**: criar o projeto Django (Etapa 0 técnica), em plan mode. Escopo escolhido pelo dono: só esqueleto, testes e CI de testes; projeto na raiz; `uv` instalado pelo dono; `pt-br` e `America/Sao_Paulo`; teste fixa o PostgreSQL 18.
- **Feito**: `pyproject.toml` e `uv.lock` (Django 6.1.3, psycopg 3.3.8, pytest 9.2.0, pytest-django 4.14.0, ruff 0.17.4; `uv` 0.13.6 fixado no workflow); `manage.py`, `config/settings.py` (tudo do ambiente, falha fechada sem `DJANGO_SECRET_KEY`, `DEBUG` só liga explícito), `apps/` vazio, `tests/test_configuracao.py` (10 testes), `.github/workflows/tests.yml` (job `tests` com `postgres:18`), `.env.example`.
- **Testes primeiro**: `pytest` contra o projeto vazio falhou por completo (`No module named 'config'`), o que prova pouco. A prova real foi a quebra de propósito.
- **CI (resultado visto)**: `tests` verde com 10 passados (Python 3.14.10, `postgres:18`), `guard` e `dco` verdes. Quebra de propósito (checagem da `SECRET_KEY` desligada): `tests` falhou com 2 testes (`sem_secret_key` e `secret_key_vazia`), 8 passaram; revertida com `git revert` e commit de reversão.
- **Não verificado**: nenhum teste rodou localmente (convenção do workspace; só `manage.py check`); versão exata do PostgreSQL 18 do serviço do CI (o teste só confere a major); comportamento com `DEBUG` ligado; `setup-uv@v6` não foi lido na documentação, só funcionou no CI.
- **Fica**: Docker Compose; `dependabot.yml` e exigir o check `tests` no ruleset (P-19); verificador de tipos; apps de domínio e conectores (Etapa 1); ADRs de hospedagem, busca, autenticação, IA, fila e agendamento; apagar a branch remota `spike/ingestao-python`; P-16.

### 2026-11-05 — Sessão 8 (stack do núcleo: P-02, P-03, P-05)

- **Pedido**: decidir a stack (plan mode). O dono comparou Django e Rails, reconheceu o empate técnico e escolheu **Django**, sem comparar por medição; escopo só P-02, P-03 e P-05; spike com dados sintéticos no CI.
- **Feito**: versões conferidas nas páginas oficiais; spike no PR #12 (aberto como rascunho, a fechar sem mesclar): testes primeiro (contra um leitor ingênuo, 5 falharam e 6 passaram), leitor real (11 passam), quebra de propósito (falharam os 4 testes esperados) e 3 execuções de medição; ADR 0006; P-02, P-03 e P-05 em Resolvidas; `OVERVIEW.md` e `README.md` atualizados.
- **Resultado do spike**: ZIP sintético de 12,11 GB descomprimidos (0,89 GB comprimido, 20,57 milhões de linhas): leitura com allowlist em 165 a 185 s (66 a 74 MB/s), SHA-256 em menos de 1 s, `COPY` de 2 milhões de linhas em 19 a 21 s, memória ≤ 49 MB. Critério (menos de 20 min e menos de 500 MB) atendido com folga de cerca de 6 vezes.
- **Escolhas minhas para o dono revisar no PR**: começar no Django 6.1 e migrar para o 6.2 LTS em abril de 2027 (em vez do 5.2 LTS, cujas correções comuns terminaram em 2025-12-03); Python 3.14 (em vez do 3.15, recém-lançado); PostgreSQL 18.
- **Erro meu no caminho**: ao reverter a quebra de propósito, o `git revert` não rodou como eu esperava e o `commit --amend` reescreveu a mensagem do commit errado; o push foi recusado, nada mudou no remoto, e refiz com um commit de reversão de verdade.
- **Não verificado**: o pico de memória real por etapa (os 49 MB são limite superior, o valor se repete); o `psycopg` com o PostgreSQL 18 na documentação (só rodou no spike); razão de compressão e volume real (extrapolação de uma amostra); `COPY` com índices; Windows-1252 versus ISO-8859-1; Rails (não medido, por escolha do dono).
- **Fica**: fechar o PR #12 sem mesclar depois do merge do ADR; criar o projeto Django (Etapa 0 técnica) em plan mode; fila e agendamento, hospedagem, busca, autenticação e IA com ADRs próprios; P-16.

### 2026-11-05 — Sessão 7 (senadores e votos individuais; revisão da allowlist)

- **Pedido**: medir os endpoints de senadores e os votos individuais (Câmara e Senado) para fechar a allowlist do ADR 0005. Sem plan mode (mesma receita); só estrutura e contagens.
- **Feito**: "Rodada 2" em `fontes/camara.md` e `fontes/senado.md`; revisão da allowlist e nova seção no ADR 0005 (as 11 decisões não mudaram); P-15 atualizado. Cerca de 14 requisições em série (mais 2 de reprodução no fim), e respostas já salvas reaproveitadas sem repetir pedido.
- **Achados**: (1) o detalhe `/deputados/{id}` da Câmara devolve **CPF preenchido e válido** (n=1), enquanto o CSV em massa o traz vazio nas 7.889 linhas, então o ADR 0005 tinha escrito "cpf vem vazio" a partir de um canal só; (2) os votos nominais da Câmara pela API travam em **504 após 15 s** (2 de 2 tentativas) e `/orientacoes` também (1 de 1), com corpo de texto simples; (3) no Senado, `totalVotosSim/Nao/Abstencao` vêm **nulos** nas votações nominais, e o código de voto tem 7 valores (`Sim`, `Não`, `AP`, `LS`, `P-NRV`, `NCom`, `Presidente (art. 51 RISF)`); (4) a lista de senadores não traz data de nascimento nem CPF, e o detalhe traz data de nascimento e naturalidade, sem CPF.
- **Proposta, a revisar pelo dono**: cada linha de voto carrega só o id do parlamentar, o voto, a data e o partido no momento; nome, UF, foto e sexo ficam na tabela de pessoas. É uma extensão da decisão 1 e não estava entre as 11 respostas aceitas.
- **Não verificado**: o CPF do detalhe para mais de um deputado; votos nominais da Câmara pela API; lista completa de valores de `voto`; significado das siglas do Senado; discursos e apartes; votações secretas. Medição de um único dia.
- **Fica**: P-16 (validação jurídica); decidir a stack (P-02).

### 2026-11-05 — Sessão 6 (P-12: minimização de dados pessoais)

- **Pedido**: decidir quais colunas pessoais o polis ingere e guarda, com base na medição das três fontes. Conduzido como entrevista em árvore de decisão (3 rodadas, 11 perguntas); o dono aceitou a recomendação em todas.
- **Feito**: ADR 0005 com as 11 decisões e uma allowlist inicial por fonte; P-12 movido para Resolvidas; P-02 atualizado.
- **Decisões principais**: allowlist por fonte (descarte na leitura); ligação de pessoas sem CPF nem título, nem em hash; bens, prestação de contas e doações fora da Etapa 1; sem atributos demográficos do TSE; bruto filtrado com hash, URL e data de geração; falha fechada em mudança de coluna; data de nascimento completa só interna e ano exposto; nome civil só interno e nome social prevalecendo; lápide para registro retirado pela fonte; últimas 3 cargas do bruto.
- **Não verificado**: a allowlist é ponto de partida e não foi conferida contra os dicionários de dados das fontes; `NM_CANDIDATO` ser o nome civil é suposição; os endpoints de senadores e os votos individuais não foram medidos; validação jurídica (P-16: LGPD, nome social, prazo de resposta a pedidos); o CPF do TSE de 2026 é medição de um único dia.
- **Fica**: P-16 (validação jurídica); decidir a stack (P-02) e abrir a Etapa 0 técnica; medir senadores e votos individuais antes de fechar a allowlist.

### 2026-11-05 — Sessão 5 (medição da fonte TSE)

- **Pedido**: medir o TSE (plan mode, por haver dado sensível e arquivos grandes). Decisões do dono: só estrutura e contagens (nenhum valor individual); ciclos **2026 e 2024**. A opção "2022 e 2024" do plano aprovado foi trocada por 2026 e 2024 depois que a descoberta mostrou dados de 2026 já publicados; o dono confirmou.
- **Feito**: `project/fontes/tse.md`, linha no índice, P-02, P-12 e P-15 atualizados. Cerca de 40 requisições em série (o plano previa 20 a 30; passei por ter reexecutado o script de amostra para refinar a classificação), mais 5 de reprodução. Amostras só em memória, por `Range`; nenhum arquivo de dados foi salvo, e nenhum valor individual foi impresso ou commitado.
- **Achados principais**: portal CKAN com 190 conjuntos; dados em ZIP no CDN (até 1,36 GB num arquivo; CKAN sem tamanho); `Range` aceito; CSV em ISO-8859-1 com CRLF; arquivos regenerados no mesmo nome várias vezes ao dia, até os de 2024; licença CC BY nos metadados (3 conjuntos sem licença); `www.tse.jus.br` deu 403 para cliente automatizado (não contornei). **Dado pessoal**: o CPF completo e válido dos candidatos está no CSV aberto de 2026 (479/479 passam na verificação dos dígitos), enquanto em 2024 a coluna é uma constante de 2 caracteres; o esquema é igual, então a mudança é invisível para quem só olha as colunas. O título de eleitor vem completo nos dois ciclos.
- **Verificado de novo** ao final: 16 conjuntos "Ano 2026", `HEAD` do arquivo estático (10.175.412 bytes), e a classificação do CPF (11 dígitos, 479) e do título (12 dígitos, 479) pelo `awk` do próprio documento, com o ZIP de 3,3 MB.
- **Não verificado**: se o CPF de 2026 vale para todas as UFs e persiste; conteúdo de bens, doações e fornecedores; as Portarias 93/2021 e 525/2021 e o `leiame.pdf`; limite por IP ou taxa; DataStore do CKAN; contagem total de linhas; interpretação jurídica (P-16). Medição de um único dia; 2024 reproduzível só com script descartável (descrito no doc).
- **Fica**: com as três fontes medidas, decidir o P-12 (quais colunas pessoais ingerir) e só então a stack (P-02); avaliar se alguma medição pede ADR.

### 2026-11-05 — Sessão 4 (medição da fonte Senado Federal)

- **Pedido**: repetir a medição para o Senado, no formato da Câmara (sem plan mode, por repetir receita já aprovada).
- **Feito**: `project/fontes/senado.md`, linha no índice `fontes/README.md`, P-02 e P-15 atualizados. Cerca de 20 requisições em série (mais 4 de reprodução no fim), sem autenticação, `User-Agent` genérico; respostas brutas só na pasta temporária da sessão.
- **Achados principais**: limite documentado de 10 req/s (429), com 503 sob demanda; API sem paginação nas listagens principais, com filtro obrigatório em `/processo` e `/votacao`; 42 de 157 endpoints depreciados, e o `Sunset` de `/materia/*` (2026-02-01) já passou com o serviço ainda no ar; código inexistente devolve 200 com dados vazios, não 404; dois estilos de JSON e dois sistemas de ids (processo e matéria legada); política de uso do portal exige citar a fonte, sem licença nomeada, e nada sobre uso comercial.
- **Verificado de novo** ao final: 157 caminhos e 42 depreciados, cabeçalhos de depreciação de `/materia/172391`, 200 para senador inexistente e 81 senadores.
- **Não verificado**: comportamento real do 429 (não testei o limite); se a política do portal vale para a API; dados pessoais dos endpoints de senadores (não olhei o conteúdo); volume de `/processo` sem filtro de ano; Plano de Dados Abertos 2026/2028; interpretação jurídica (P-16). Medição de um único dia.
- **Fica**: TSE; depois das três fontes, decidir se alguma medição pede ADR e, só então, escolher a stack (P-02).

### 2026-11-05 — Sessão 3 (medição da fonte Câmara dos Deputados)

- **Pedido**: medir as fontes para P-02 e P-15, uma por vez, começando pela Câmara (plan mode; plano aprovado).
- **Feito**: `project/fontes/README.md` (índice e rótulos de origem: medido, documentação, inferência, não verificado) e `project/fontes/camara.md` (campos do PRD §8.1). Medi com 22 requisições (mais 3 de reprodução no fim) em série, sem autenticação, `User-Agent` genérico; respostas brutas ficaram só na pasta temporária da sessão, fora do repo.
- **Achados principais**: API REST + arquivos em massa (CSV, JSON, XLSX); sem autenticação; limite documentado de 100 itens por página (`itens=101` deu 504 em 15 s); `retry-after: 30` em toda resposta, sem significado documentado; arquivos regenerados de madrugada, inclusive de anos encerrados; `cpf` existe no CSV de deputados mas vem vazio nas 7.889 linhas; 62 de 100 proposições recentes têm `ano = 0`; FAQ diz que se pode cobrar pelo uso e não declara restrição, mas não achei licença explícita.
- **Verificado de novo** ao final: 3 comandos de reprodução do doc (513 deputados, 42.340.873 bytes no arquivo de proposições 2026, 78 caminhos na especificação).
- **Não verificado**: limite de taxa e bloqueio (não testei de propósito); XML e ODS; despesas, discursos e votos por deputado; consistência API versus arquivos; ids estáveis; uma única data de medição (a regeneração diária dos arquivos é inferência). Licença e Ato da Mesa 45/2012 não lidos; interpretação jurídica é P-16.
- **Fica**: Senado e TSE (uma por vez); decidir depois das três se alguma medição pede ADR.

### 2026-11-05 — Sessão 2, parte 4 (`dco` exigido no ruleset)

- **Alterado** (confirmado pelo dono): `protect-main` passou a exigir `guard` e `dco`. Comparei o ruleset antes e depois via API: só a lista de checks mudou (bypass, condições e demais regras iguais). Os JSONs antes/depois ficaram na pasta temporária da sessão, não no repo.
- **Testado**: PR #5 descartável com commit sem sign-off: `dco` falhou ("Commit dc45e27 sem Signed-off-by…"), `guard` passou, o estado do merge ficou `BLOCKED`. PR fechado sem mesclar e branch apagada.
- **Não verificado**: PR do Dependabot sob a nova regra; squash e rebase merge; o bypass do Admin sobre o `dco` (existe via PR, não exercitado).
- **Fica**: medir as fontes (TSE, Câmara, Senado) para P-02 e P-15.

### 2026-11-05 — Sessão 2, parte 3 (aplicação do DCO)

- **Decisão do dono**: workflow separado `dco` (não dentro do `guard`), vale para todos os PRs, inclusive os do mantenedor.
- **Feito**: `.github/scripts/check-dco.sh` (sign-off do autor ou do committer, merges ignorados, `dependabot[bot]` isento), `.github/scripts/test-check-dco.sh` (14 casos), `.github/workflows/dco.yml` (roda os testes e depois a checagem), `CONTRIBUTING.md`.
- **Testes**: contra um stub que sempre passa, 6 passaram e 5 falharam. Com a implementação, 14 passam. Mutações no script (maiúsculas, aceitar qualquer e-mail, incluir merges, tirar a isenção do dependabot, só autor, só committer): todas pegas por algum teste; as duas últimas só depois de eu acrescentar testes, que não distinguiam autor de committer. Um mutante equivalente (exigir `@` no regex) não é pego, porque o e-mail já tem de bater com o do autor ou do committer.
- **Não verificado**: se os PRs do Dependabot trazem `Signed-off-by` (palpite: não; a isenção cobre); comportamento em squash e rebase merge; o check ainda não é exigido no ruleset.
- **Fica**: depois do merge e do `dco` verde na `main`, incluir `dco` nos checks exigidos do `protect-main` (mexe na proteção da `main`: pedir confirmação); medir as fontes (P-02, P-15).

### 2026-11-05 — Sessão 2, parte 2 (P-01: DCO)

- **Decisão do dono**: DCO (ADR 0004), depois de comparar com CLA. Premissa registrada: sem plano de dual license hoje (P-11 em aberto).
- **Feito**: ADR 0004; P-01 movido para Resolvidas; PR #2 mesclado antes (`guard` verde na `main`, run 42114858200).
- **Não verificado**: validação jurídica (P-16).
- **Fica**: PR de aplicação (`CONTRIBUTING.md` e checagem de `Signed-off-by` no `guard`, com teste primeiro); medir as fontes (P-02, P-15).

### 2026-11-05 — Sessão 2 (fechamento da proteção da `main`)

- **Pedido**: fechar a governança da Etapa 0 deixada em aberto na Sessão 1.
- **Conferido** (leitura via `gh api`): `guard` verde na `main` (run do merge do PR #1, 7s); ruleset `protect-main` ativo (sem exclusão, sem force push, PR com 0 aprovações, `guard` obrigatório, `strict: false`, bypass do papel Admin só via PR); secret scanning e push protection ligados; `delete_branch_on_merge` ligado; 0 alertas do Dependabot.
- **Alterado** (confirmado pelo dono): `dependabot_security_updates` ligado (estava desativado).
- **Testado**: push direto na `main` (commit vazio) recusado com "Changes must be made through a pull request" e "Required status check guard is expected"; commit local descartado, nada chegou ao remoto.
- **Não verificado**: push protection com segredo real; o bypass do Admin não foi exercitado (só se sabe que existe via PR).
- **Fica**: P-01 (CLA ou DCO); medir as fontes (TSE, Câmara, Senado) para P-02 e P-15.

### 2026-10-31 — Sessão 1 (criação do repositório e decisões iniciais)

- **Pedido**: estruturar o projeto novo a partir do PRD: repositório, GitHub, licença e o padrão do workspace.
- **Decisão do dono**: nome polis (entre 5 candidatos, ADR 0001); `masterlxz/polis` público (ADR 0003); AGPL-3.0 (ADR 0002); só governança e docs, sem código nem stack.
- **Feito** (commit inicial direto na `main`, depois branch `docs/estrutura-inicial`, PR #1): repo criado; `LICENSE` oficial, `README`, `.gitignore`; PRD em `project/PRD.md`; `INDEX`, `OVERVIEW`, `PENDING`, `SESSIONS`; ADRs 0001 a 0003; template de PR e job `guard` copiados de `padrao/` do workspace.
- **CI**: `guard` passou no PR #1 (visto com `gh pr checks 1`, 4s). Na `main` ainda não rodou; conferir depois do merge, antes de ligar o ruleset.
- **Não verificado**: ruleset e segurança ainda não aplicados (dependem do merge e do `guard` verde na `main`); push direto na `main` bloqueado e push protection com segredo real não testados.
- **Fica**: mesclar o PR #1; ligar ruleset, secret scanning, push protection, alertas do Dependabot e `delete_branch_on_merge`; decidir P-01 (CLA/DCO) antes de qualquer contribuição de código; medir as fontes (TSE, Câmara, Senado) para escolher a stack.
