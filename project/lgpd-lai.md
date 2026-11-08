# polis: LGPD e LAI (pesquisa para o P-16)

**Isto não é parecer jurídico e não fecha o P-16.** É uma leitura de apoio, de 2026-11-07, feita por busca na web em espelhos do texto e artigos de doutrina. O texto oficial (planalto.gov.br) **não foi aberto**. Rótulos como em `fontes/README.md`. Decisão do dono (Sessão 27): por enquanto **não** se leva a um advogado; as perguntas abaixo ficam registradas para quando for.

## O que a pesquisa indica

| Dispositivo | O que diz | Rótulo | Efeito no polis |
|---|---|---|---|
| LGPD art. 7º §3º | Dado de acesso público deve ser tratado considerando a finalidade, a boa-fé e o interesse público que justificaram a divulgação. Ser público não é salvo-conduto. | documentação (Migalhas, espelho do texto) | Reforça allowlist e minimização (ADR 0005). |
| LGPD art. 7º §4º | Dado tornado manifestamente público **pelo titular** dispensa consentimento, ainda sujeito a finalidade, adequação e necessidade. | documentação (Migalhas) | Pouca ajuda: quem publica é o TSE, a Câmara ou o Senado, não o titular. |
| LGPD art. 7º §7º | Reuso para nova finalidade exige propósito legítimo e específico e preservação dos direitos do titular. | documentação (Migalhas) | Ponto central: reusar dado eleitoral e legislativo para fiscalização cívica exige finalidade documentada. |
| LGPD art. 5º II e art. 11 | Origem racial ou étnica e opinião política são dado sensível; exige consentimento ou hipótese taxativa. Há tese acadêmica de que os §§3º, 4º e 7º valem também para sensível público (UFRGS), não pacífica. | documentação (artigos); tese = inferência de terceiros | Confirma adiar cor/raça (ADR 0005, decisão 4). |
| LGPD art. 4º | Exclui tratamento exclusivamente jornalístico, artístico ou acadêmico. | documentação | O polis é plataforma pública com API: não presumir a exceção. |
| LGPD arts. 23 a 30 | Regem o poder público. | documentação | Valem para as fontes; o polis é particular e fica no regime geral (inferência). |
| LAI art. 31 e Decreto 8.777/2016 | Informação pessoal tem acesso restrito; o decreto exclui da abertura automática o que o art. 31 protege, e declara de livre utilização os dados abertos do Executivo federal (alterado em 2019). | documentação (Câmara, legislação) | O decreto é do Executivo federal; TSE, Câmara e Senado não estão claramente cobertos (inferência). |

## Não verificado

- Texto oficial de qualquer dispositivo acima.
- LGPD art. 18 (direitos do titular) e prazos de resposta.
- Texto literal do art. 31 e do art. 8º §3º da LAI.
- Se o Decreto 8.777/2016 segue vigente na redação atual.
- Se há orientação da ANPD sobre reuso de dado público (não pesquisei).

## Perguntas que continuam abertas (precisam de especialista)

1. Qual base legal do art. 7º o polis usa para tratar dado pessoal público (legítimo interesse, outra)?
2. O que caracteriza uma "finalidade nova" lícita para o §7º no caso do polis?
3. Divulgar dado sensível público (candidatura e partido como opinião política; cor/raça) é permitido, e sob quais condições?
4. Prazo e procedimento para pedidos do art. 18 (ADR 0005, decisão 10, hoje sem prazo).
5. Uso comercial e redistribuição em massa (ADR 0008, decisão 9).
6. O CPF de 2026 no CSV do TSE: o polis o descarta na leitura (ADR 0005); a pergunta ao TSE sobre por que ele aparece segue sem envio.

## Conclusão provisória

O desenho do ADR 0005 (minimização, allowlist, finalidade declarada) é coerente com o que o §3º e o §7º pedem; nada do que li o contradiz. Isso é **coerência**, não validação.

## Fontes consultadas

- Migalhas: dados pessoais tornados manifestamente públicos (art. 7º §4º): https://www.migalhas.com.br/depeso/293745/a-excecao-dos-dados-pessoais-tornados-manifestamente-publicos-pelo-titular-na-lgpd
- Migalhas: dados públicos e LGPD: https://www.migalhas.com.br/depeso/464535/dados-publicos-e-lgpd-um-teste-para-decidir-o-que-publicar
- UFRGS (§§3º, 4º, 7º e dados sensíveis): https://lume.ufrgs.br/bitstream/handle/10183/250883/001152873.pdf?sequence=1
- Migalhas: LGPD e dados sensíveis: https://www.migalhas.com.br/depeso/347182/lgpd-e-a-protecao-de-dados-sensiveis
- Decreto 8.777/2016 (Câmara): https://www2.camara.leg.br/legin/fed/decret/2016/decreto-8777-11-maio-2016-783082-publicacaooriginal-150347-pe.html
- Relatório GT 4, abertura de dados pessoais (Prefeitura do Rio): https://lgpd.prefeitura.rio/wp-content/uploads/sites/102/2026/03/Relatorio-do-GT-4-Abertura-de-Dados-Pessoais-pela-Administracao-Publica-Municipal-2024.pdf
