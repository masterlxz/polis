# PRD — Plataforma Nacional de Transparência e Inteligência Cívica

**Documento:** PRD  
**Versão:** 0.1  
**Status:** Documento inicial para discussão e refinamento  
**Nome do projeto:** polis (ADR 0001)  
**Última atualização:** 31/10/2026

---

## 1. Visão geral

A proposta é desenvolver uma plataforma digital que reúna, organize e apresente informações públicas sobre o Brasil, suas instituições, representantes, decisões, atividades, gastos e políticas públicas.

O objetivo é transformar dados atualmente espalhados por diferentes portais, sistemas e documentos em uma experiência unificada, acessível, pesquisável e compreensível para qualquer cidadão.

A plataforma deverá permitir que uma pessoa encontre informações sobre um político, partido, órgão público, processo, votação, contrato, gasto ou acontecimento e consiga compreender o contexto, consultar os documentos originais e acompanhar mudanças ao longo do tempo.

A inteligência artificial será uma parte central da experiência, auxiliando na pesquisa, organização, explicação e contextualização das informações. Ela não será considerada fonte primária nem poderá apresentar conclusões sem evidências verificáveis.

## 2. Problema

Informações relevantes para o acompanhamento da vida pública brasileira estão distribuídas entre dezenas de instituições e portais. Cada fonte utiliza formatos, padrões, identificadores, interfaces e frequências de atualização diferentes.

Isso dificulta:

- Encontrar informações sobre determinado agente público ou instituição.
- Relacionar acontecimentos e documentos de fontes diferentes.
- Acompanhar o histórico de decisões, votações, gastos e atividades.
- Entender documentos técnicos, jurídicos e administrativos.
- Verificar a origem de uma informação.
- Comparar dados de diferentes períodos, órgãos e regiões.
- Identificar alterações e atualizações em registros públicos.

## 3. Objetivos do produto

1. Centralizar referências a informações públicas de diferentes instituições brasileiras.
2. Organizar dados em estruturas consistentes e relacionadas.
3. Facilitar a pesquisa por pessoas, organizações, temas, documentos e acontecimentos.
4. Apresentar históricos e cronologias verificáveis.
5. Permitir que usuários acompanhem representantes, instituições e assuntos.
6. Utilizar IA para tornar informações complexas mais acessíveis.
7. Preservar a origem, o contexto e a rastreabilidade dos dados.
8. Oferecer uma experiência simples para o público geral e ferramentas aprofundadas para pesquisadores, jornalistas e outros interessados.
9. Manter transparência sobre limitações, lacunas, atualizações e possíveis divergências entre fontes.

## 4. Princípios do produto

- **Neutralidade:** a plataforma não deve favorecer partidos, ideologias, candidatos ou instituições.
- **Rastreabilidade:** toda informação relevante deve apontar para sua fonte.
- **Precisão:** fatos, alegações, opiniões e interpretações devem ser diferenciados.
- **Contextualização:** dados devem ser apresentados com período, origem e contexto suficientes para evitar conclusões enganosas.
- **Histórico:** alterações e correções devem ser registradas sempre que tecnicamente e legalmente possível.
- **Acessibilidade:** a experiência deve ser compreensível por pessoas sem conhecimento técnico ou jurídico.
- **Privacidade:** o tratamento de dados deve respeitar a legislação e minimizar a exposição de informações pessoais.
- **Independência:** a plataforma deve deixar claras sua metodologia, suas limitações e sua política editorial.
- **Verificabilidade:** o usuário deve conseguir consultar os documentos e registros originais.
- **Separação entre dado e análise:** interpretações automatizadas não devem ser apresentadas como fatos oficiais.

## 5. Público-alvo

- Cidadãos interessados em acompanhar a atuação do poder público.
- Eleitores que desejam pesquisar candidatos e representantes.
- Jornalistas e profissionais de comunicação.
- Pesquisadores, professores e estudantes.
- Organizações da sociedade civil.
- Desenvolvedores e pessoas interessadas em reutilizar dados públicos.

## 6. Escopo funcional

A plataforma deverá ser concebida para atender ao território nacional, contemplando informações federais, estaduais e municipais conforme a disponibilidade, qualidade e permissões de uso de cada fonte.

### 6.1. Pessoas e agentes públicos

Perfis de pessoas que ocupam ou ocuparam cargos públicos ou aparecem em registros públicos relevantes.

Informações possíveis:

- Nome público e identificadores oficiais pertinentes.
- Biografia baseada em fontes públicas.
- Cargos, funções e mandatos.
- Histórico de atuação.
- Filiações partidárias, quando aplicável.
- Candidaturas e resultados eleitorais.
- Projetos, proposições e relatorias.
- Votações e presença em sessões, quando disponíveis.
- Discursos e manifestações oficiais.
- Nomeações, exonerações e mudanças de função.
- Relações institucionais documentadas.
- Linha do tempo de acontecimentos relevantes.

A plataforma deverá evitar confusão entre pessoas com nomes semelhantes e não deverá inferir relações pessoais ou institucionais sem evidências.

### 6.2. Organizações e instituições

Perfis de:

- Partidos políticos.
- Ministérios e secretarias.
- Tribunais e órgãos do Judiciário.
- Casas legislativas.
- Autarquias e fundações.
- Órgãos de fiscalização e controle.
- Empresas públicas e sociedades de economia mista.
- Governos estaduais e municipais.
- Outras organizações públicas relevantes.

Informações possíveis:

- Competências e atribuições.
- Estrutura organizacional.
- Dirigentes e responsáveis.
- Histórico de alterações.
- Documentos e atos publicados.
- Relações institucionais documentadas.
- Orçamento, contratos e atividades, conforme disponibilidade.

### 6.3. Eleições e candidaturas

- Candidatos e candidaturas.
- Partidos, federações e coligações, conforme o período eleitoral.
- Resultados por cargo e território.
- Votação por município, zona ou seção, conforme disponibilidade.
- Abstenções e dados do eleitorado.
- Receitas e despesas de campanha.
- Doadores e fornecedores, respeitadas as regras de acesso e uso.
- Bens declarados em registros eleitorais.
- Histórico de candidaturas.
- Situação e prestação de contas.

### 6.4. Poder Legislativo

- Projetos de lei, propostas de emenda e demais proposições.
- Autoria, coautoria e relatoria.
- Tramitação e alterações.
- Emendas e requerimentos.
- Comissões, CPIs e audiências.
- Sessões plenárias.
- Votações nominais e resultados.
- Presença e participação parlamentar, quando disponíveis.
- Discursos e pronunciamentos.
- Relações entre parlamentares, proposições e temas.

### 6.5. Poder Executivo

- Presidência e governos estaduais e municipais.
- Ministérios, secretarias e órgãos vinculados.
- Nomeações e exonerações.
- Decretos, portarias, medidas provisórias e outros atos.
- Sanções e vetos.
- Agendas e compromissos oficiais, quando publicados.
- Programas e políticas públicas.
- Planos de governo e compromissos públicos.
- Indicadores e evidências de execução, quando existirem fontes confiáveis.

### 6.6. Poder Judiciário

- Tribunais e sua composição.
- Magistrados e ministros.
- Processos e movimentações que possam ser legalmente utilizados.
- Decisões, votos e acórdãos.
- Relatorias.
- Jurisprudência.
- Recursos e desdobramentos.
- Estatísticas judiciais.
- Cronologias processuais, respeitadas as restrições legais e técnicas de cada fonte.

A plataforma deverá distinguir claramente as diferentes situações processuais, como investigação, denúncia, recebimento de denúncia, julgamento, condenação, absolvição, arquivamento e decisão reformada.

### 6.7. Finanças públicas

- Orçamento público.
- Receitas e despesas.
- Execução orçamentária.
- Emendas parlamentares.
- Contratos e convênios.
- Licitações e compras públicas.
- Fornecedores.
- Diárias e passagens.
- Remunerações e subsídios publicados oficialmente.
- Transferências de recursos.
- Obras e investimentos.
- Dados fiscais e orçamentários por órgão, período e território.

### 6.8. Fiscalização e controle

- Auditorias.
- Relatórios de fiscalização.
- Acórdãos e decisões de tribunais de contas.
- Sanções administrativas.
- Contas julgadas.
- Recomendações e determinações.
- Acompanhamento de providências e resultados.
- Histórico de processos de controle.

### 6.9. Políticas públicas e indicadores

- Educação.
- Saúde.
- Segurança pública.
- Infraestrutura.
- Economia.
- Meio ambiente.
- Saneamento.
- Habitação.
- Mobilidade.
- Indicadores demográficos e regionais.
- Dados de execução e resultados de políticas públicas.

Os indicadores deverão apresentar fonte, período, metodologia e limitações conhecidas.

### 6.10. Documentos e acontecimentos

- Diários oficiais.
- Atos administrativos.
- Documentos legislativos.
- Documentos judiciais autorizados.
- Relatórios públicos.
- Publicações institucionais.
- Comunicados e registros oficiais.
- Acontecimentos relevantes extraídos de fontes verificáveis.
- Histórico de versões e retificações, quando disponível.

### 6.11. Inteligência e pesquisa

- Busca global.
- Busca por linguagem natural.
- Busca semântica.
- Resumos de documentos.
- Explicação de termos técnicos.
- Extração de entidades e datas.
- Identificação de relações documentadas.
- Construção de cronologias.
- Comparações descritivas.
- Pesquisa guiada por perguntas.
- Alertas sobre alterações em registros acompanhados.
- Respostas com referências diretas às fontes.

### 6.12. Conta e personalização

- Cadastro e autenticação, caso necessário.
- Perfis de interesse.
- Acompanhamento de pessoas, partidos, órgãos e temas.
- Alertas e notificações.
- Histórico de consultas.
- Preferências de acessibilidade e apresentação.
- Gestão de dados pessoais e exclusão de conta.

## 7. Experiência e navegação

A interface deverá atender tanto a usuários que desejam uma consulta rápida quanto a usuários que precisam investigar informações em profundidade.

Estrutura inicial de navegação:

- Início.
- Pessoas.
- Eleições.
- Legislativo.
- Judiciário.
- Governo.
- Dinheiro público.
- Fiscalização.
- Políticas públicas.
- Explorar.
- Minha conta.

A estrutura final de navegação e os nomes das seções ficam **a decidir** durante o desenvolvimento da experiência do usuário.

### 7.1. Busca global

A busca deverá permitir consultas por:

- Nome de pessoa.
- Instituição ou órgão.
- Partido.
- Cargo ou mandato.
- Número de processo ou proposição.
- Contrato ou fornecedor.
- Tema ou palavra-chave.
- Período.
- Território.
- Documento.

Os resultados deverão apresentar filtros, contexto, data e origem.

### 7.2. Páginas de perfil

Páginas de pessoas e organizações deverão reunir informações relacionadas em seções claras, com cronologia, documentos, atividades e referências.

### 7.3. Transparência das informações

Sempre que possível, cada registro deverá exibir:

- Instituição de origem.
- Identificador original.
- URL da fonte.
- Data de publicação.
- Data de coleta pela plataforma.
- Período ao qual o dado se refere.
- Documento ou evidência relacionada.
- Situação de validação.
- Observações sobre limitações ou divergências.

## 8. Fontes de dados

A plataforma deverá priorizar fontes oficiais e documentos primários.

Fontes a investigar incluem:

- Tribunal Superior Eleitoral (TSE).
- Câmara dos Deputados.
- Senado Federal.
- Portal da Transparência.
- Portal Nacional de Contratações Públicas (PNCP).
- Conselho Nacional de Justiça (CNJ) e tribunais.
- Tribunal de Contas da União (TCU).
- Controladoria-Geral da União (CGU).
- Instituto Brasileiro de Geografia e Estatística (IBGE).
- Instituto de Pesquisa Econômica Aplicada (IPEA).
- Tesouro Nacional.
- Banco Central.
- INEP.
- DATASUS.
- Assembleias legislativas.
- Câmaras municipais.
- Tribunais de contas estaduais e municipais.
- Portais estaduais e municipais de transparência.
- Diários oficiais.
- Agências reguladoras e demais órgãos públicos.

A lista é inicial e não representa garantia de disponibilidade, integração ou permissão de redistribuição.

### 8.1. Cadastro de fontes

Cada fonte deverá possuir um registro técnico contendo, quando aplicável:

- Nome e instituição responsável.
- Endereço oficial e documentação técnica.
- Tipo de acesso: API, download, página, arquivo ou outro.
- Formatos disponíveis.
- Necessidade de autenticação.
- Limites de requisição.
- Frequência de atualização.
- Termos de uso e licença.
- Restrições de armazenamento, transformação e redistribuição.
- Campos e entidades fornecidos.
- Identificadores oficiais.
- Histórico de sincronizações.
- Estado atual da integração.
- Problemas conhecidos e limitações.

### 8.2. Regras de utilização

A disponibilidade pública de um dado não significa automaticamente que qualquer forma de coleta, armazenamento, transformação ou redistribuição esteja autorizada.

Antes de integrar uma fonte, deverão ser avaliados seus termos, licenças, regras específicas, limites técnicos e legislação aplicável. Fontes com restrições deverão ser tratadas conforme suas condições, inclusive podendo ser excluídas do produto ou utilizadas apenas de formas permitidas.

## 9. Arquitetura conceitual

A solução deverá separar:

1. Interface pública.
2. API e regras de negócio.
3. Domínios funcionais.
4. Conectores de fontes externas.
5. Pipeline de ingestão e normalização.
6. Banco de dados.
7. Busca e indexação.
8. Camada de inteligência artificial.
9. Processos assíncronos.
10. Monitoramento e administração.

A arquitetura técnica definitiva fica **a decidir**.

### 9.1. Ingestão de dados

Fluxo conceitual:

1. Consultar ou receber dados da fonte.
2. Registrar a execução da coleta.
3. Preservar o dado original quando permitido.
4. Validar estrutura e integridade.
5. Normalizar para o modelo interno.
6. Identificar entidades.
7. Deduplicar registros.
8. Persistir dados e evidências.
9. Atualizar índices de busca.
10. Registrar alterações e gerar eventos internos.
11. Atualizar métricas e estado do conector.

Falhas de coleta não deverão apagar automaticamente dados históricos já armazenados.

### 9.2. Conectores

Cada conector deverá ser isolado e responsável por uma fonte ou conjunto coerente de endpoints.

Requisitos:

- Paginação.
- Retentativas com limites.
- Respeito a rate limits.
- Tratamento de erros.
- Logs estruturados.
- Versionamento de esquemas.
- Identificação de registros por IDs de origem.
- Sincronização incremental quando possível.
- Reconciliação histórica quando necessária.
- Reprocessamento controlado.
- Métricas de qualidade e atualização.

### 9.3. Modelo unificado

A plataforma deverá possuir um modelo interno capaz de relacionar entidades de diferentes fontes sem apagar suas características originais.

Entidades conceituais iniciais:

- Pessoa.
- Organização.
- Vínculo.
- Cargo.
- Mandato.
- Eleição.
- Candidatura.
- Proposição legislativa.
- Votação legislativa.
- Processo judicial.
- Decisão judicial.
- Contrato.
- Despesa pública.
- Emenda.
- Documento público.
- Acontecimento.
- Relação.
- Fonte de dados.
- Afirmação ou registro de evidência.

O modelo físico, os relacionamentos e os campos definitivos ficam **a decidir**.

### 9.4. Rastreabilidade e conflitos

A plataforma deverá permitir que diferentes fontes sustentem, complementem ou contradigam uma informação.

Cada afirmação relevante deverá manter, quando possível:

- Entidade relacionada.
- Tipo de informação.
- Valor ou conteúdo.
- Fonte.
- Evidência ou documento.
- Data de coleta.
- Data de publicação.
- Período de validade.
- Estado de validação.
- Histórico de correções.

A plataforma não deverá sobrescrever silenciosamente informações conflitantes. Divergências relevantes deverão ser preservadas e apresentadas com contexto.

## 10. Inteligência artificial

A IA deverá atuar como camada de pesquisa, interpretação e organização, nunca como fonte primária de verdade.

Funcionalidades previstas:

- Pesquisa em linguagem natural.
- Recuperação de documentos relevantes.
- Resumo de documentos extensos.
- Explicação de termos técnicos.
- Extração de nomes, datas, valores e entidades.
- Identificação de relações presentes em documentos.
- Geração de cronologias com evidências.
- Comparação de registros.
- Detecção de alterações.
- Assistente de investigação.

### 10.1. Regras obrigatórias

- Respostas factuais devem apresentar fontes verificáveis.
- A IA não pode inventar documentos, citações, números ou acontecimentos.
- A origem e a data das informações devem ser apresentadas.
- Dados oficiais e conteúdo jornalístico devem ser identificados separadamente.
- Alegações não podem ser apresentadas como fatos comprovados.
- A IA deve indicar quando não houver evidência suficiente.
- Incertezas e limitações devem ser comunicadas.
- Análises automatizadas devem ser identificadas como tais.
- A plataforma não deverá criar rankings arbitrários de qualidade política nem recomendar candidatos.
- Documentos externos devem ser tratados como conteúdo não confiável, nunca como instruções para o sistema.
- A IA não deverá executar consultas ou operações irrestritas diretamente no banco de produção.

A seleção de modelos, provedores, estratégias de RAG, embeddings e custos fica **a decidir**.

## 11. Segurança, privacidade e conformidade

Requisitos iniciais:

- Adequação à LGPD.
- Minimização de dados pessoais.
- Separação entre dados públicos e dados privados de usuários.
- Controle de acesso administrativo.
- Proteção de credenciais e segredos.
- Limites de requisição.
- Registro de ações administrativas.
- Política de retenção.
- Processo de correção de informações.
- Processo de exclusão de dados pessoais quando aplicável.
- Backups e testes de restauração.
- Proteção contra abuso e ataques automatizados.
- Revisão de permissões e termos das fontes.
- Política de segurança para documentos e conteúdo externo.

A interpretação jurídica e os procedimentos definitivos deverão ser validados antes da disponibilização pública de funcionalidades que envolvam dados sujeitos a restrições.

## 12. Requisitos não funcionais

Metas iniciais a validar durante o desenvolvimento:

- Interface responsiva para celular, tablet e desktop.
- Acessibilidade como requisito de projeto.
- Páginas públicas indexáveis por mecanismos de busca.
- API documentada.
- Logs estruturados.
- Métricas de saúde dos conectores.
- Monitoramento de erros.
- Backups automáticos.
- Testes de restauração.
- Testes automatizados.
- Testes de integração com fontes.
- Controle de qualidade dos dados.
- Limites de uso para proteger a infraestrutura.
- Desempenho adequado em consultas comuns.
- Capacidade de reprocessar dados sem duplicação ou perda histórica.

Metas quantitativas de disponibilidade, latência, volume e capacidade ficam **a decidir**.

## 13. Administração e observabilidade

Deverá existir uma área interna para acompanhar:

- Estado de cada conector.
- Última sincronização.
- Próxima execução prevista.
- Quantidade de registros coletados.
- Registros rejeitados.
- Duplicidades identificadas.
- Entidades sem correspondência.
- Erros de normalização.
- Fontes desatualizadas.
- Divergências entre fontes.
- Tempo de processamento.
- Estado dos índices de busca.
- Uso e custos da IA.
- Alertas operacionais.

A interface e os níveis de permissão administrativos ficam **a decidir**.

## 14. API pública

A plataforma poderá disponibilizar uma API pública para consulta e reutilização dos dados que puderem ser legalmente redistribuídos.

Rotas conceituais iniciais:

```text
GET /api/v1/people/
GET /api/v1/people/{id}/
GET /api/v1/people/{id}/events/
GET /api/v1/people/{id}/votes/

GET /api/v1/organizations/
GET /api/v1/elections/

GET /api/v1/legislative/matters/
GET /api/v1/legislative/votes/

GET /api/v1/judicial/cases/
GET /api/v1/public-contracts/
GET /api/v1/events/

GET /api/v1/search/
GET /api/v1/sources/
```

Os endpoints, autenticação, limites, versionamento e política de acesso ficam **a decidir**.

## 15. Etapas de desenvolvimento

A ordem abaixo é uma proposta inicial e poderá ser alterada conforme a avaliação técnica.

### Etapa 0 — Fundação

- Repositório e estrutura inicial.
- Documentação do projeto.
- Design system inicial.
- Ambiente de desenvolvimento.
- Banco de dados.
- Cadastro de fontes.
- Pipeline de ingestão.
- CI e testes.
- Primeiros mecanismos de monitoramento.

### Etapa 1 — Legislativo e eleições

- Integração com dados do TSE.
- Integração com Câmara dos Deputados.
- Integração com Senado Federal.
- Pessoas e partidos.
- Candidaturas e resultados.
- Proposições e tramitações.
- Votações.
- Perfis públicos.
- Busca inicial.

### Etapa 2 — Experiência pública

- Páginas de perfil completas.
- Cronologias.
- Filtros e pesquisa avançada.
- Acompanhamento de entidades.
- Alertas.
- Comparações descritivas.
- Melhorias de acessibilidade e usabilidade.

### Etapa 3 — Finanças públicas

- Portal da Transparência.
- PNCP.
- Contratos e licitações.
- Despesas.
- Emendas.
- Fornecedores.
- Execução orçamentária.

### Etapa 4 — Inteligência artificial

- Busca semântica.
- Assistente de pesquisa.
- Resumos.
- Extração de documentos.
- Cronologias assistidas.
- Respostas com evidências.
- Detecção de alterações.

### Etapa 5 — Judiciário e fiscalização

- Integrações judiciais permitidas.
- Decisões e documentos.
- Tribunais de contas.
- Auditorias.
- Relatórios e sanções.
- Acompanhamento de processos de controle.

### Etapa 6 — Expansão nacional

- Governos estaduais.
- Assembleias legislativas.
- Prefeituras.
- Câmaras municipais.
- Tribunais de contas estaduais.
- Diários oficiais.
- Indicadores regionais.
- Novas fontes setoriais.

## 16. Critérios de qualidade para cada integração

Uma integração não deverá ser considerada concluída apenas porque consegue baixar dados.

Critérios mínimos:

- Documentação da fonte.
- Termos de uso avaliados.
- Identificadores de origem preservados.
- Validação dos dados.
- Tratamento de erros.
- Testes automatizados.
- Prevenção de duplicidades.
- Histórico de sincronização.
- Métricas de qualidade.
- Indicação de limitações.
- Rastreabilidade até a fonte.
- Processo de atualização e reprocessamento.

## 17. Política editorial e correções

A plataforma deverá publicar uma metodologia clara explicando:

- Como os dados são coletados.
- Como são normalizados.
- Como pessoas e organizações são identificadas.
- Como divergências são tratadas.
- Como a IA é utilizada.
- Quais são as limitações conhecidas.
- Como solicitar correções.
- Como são avaliadas solicitações de correção.
- Como o histórico de alterações é preservado.

A plataforma deverá evitar linguagem que sugira culpa, irregularidade ou responsabilidade sem que isso esteja sustentado por documentos e pelo contexto adequado.

## 18. Decisões em aberto

Os itens abaixo devem permanecer em aberto para discussão durante o planejamento e a implementação. Não devem ser tratados como decisões definitivas neste documento.

- Nome definitivo do projeto.
- Identidade visual e linguagem da marca.
- Licença e estratégia de código aberto.
- Stack e versões definitivas.
- Estrutura final do repositório.
- Arquitetura de implantação.
- Provedor de hospedagem e infraestrutura.
- Banco de dados e tecnologias complementares.
- Estratégia de busca.
- Estratégia de armazenamento de documentos.
- Provedores e modelos de IA.
- Estratégia de autenticação.
- Necessidade e formato de API pública.
- Política de uso e limites da API.
- Modelo de financiamento e sustentabilidade.
- Política definitiva de retenção de dados.
- Priorização final dos módulos.
- Metas quantitativas de desempenho e disponibilidade.
- Regras específicas para cada fonte de dados.
- Interpretações jurídicas que exijam validação especializada.
- Design e navegação definitivos.

## 19. Diretriz de implementação

O desenvolvimento deverá começar com uma base pequena, funcional e extensível. Cada módulo deverá ser implementado com documentação, testes, rastreabilidade e critérios claros de conclusão.

A prioridade não é integrar a maior quantidade possível de fontes rapidamente, mas construir uma estrutura confiável que permita adicionar novas fontes sem comprometer a consistência, a qualidade e a verificabilidade das informações.

O produto deverá evoluir de forma incremental, mantendo desde o início os princípios de neutralidade, transparência, rastreabilidade e respeito às condições de uso dos dados.
