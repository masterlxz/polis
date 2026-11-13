# 0027: Saída do exercício do deputado: estado gravado, sem apagar

**Data:** 2026-11-12

## Contexto
`camara/deputados` é a lista de deputados **em exercício**. O ADR 0022 (decisão 3) manda nunca apagar: quem some da lista continua em `Deputy` com a execução antiga. Faltava marcar a saída: a API interna do perfil devolvia o deputado que saiu igual a quem está na lista. O ADR 0026 limitou a lápide ao TSE justamente porque sumir desta lista **não é** a Câmara retirando o registro. A lista não diz o motivo (licença, fim de mandato, renúncia, morte, suplente assumindo) nem a data real.

## Decisão
1. **Estado gravado em `Deputy`:** `in_office` (padrão `True`) e `left_list_at` (nulo). Migração só aditiva (`legislature/0002`); linhas existentes ficam em exercício até a próxima normalização.
2. **Na normalização** (mesma transação do upsert): quem estava em exercício e não veio na carga recebe `in_office=False` e `left_list_at` = **início da execução** que primeiro não o trouxe. Quem volta à lista volta a `in_office=True` e `left_list_at` é limpo; sair de novo grava um instante novo. Nada é apagado.
3. **Só a carga mais recente mexe no estado.** Normalizar à mão uma carga antiga atualiza nome, partido e UF (como antes), mas não liga nem desliga ninguém; sem essa guarda o upsert religaria quem já saiu. Falha técnica e "arquivo igual" (0 linhas) nunca chegam à normalização, então nunca marcam ninguém.
4. **API interna do perfil:** `em_exercicio` (bool) e `saiu_da_lista_em` (ISO ou `null`) dentro de `deputado`. `false` quer dizer só "não consta mais na lista de exercício da Câmara". `saiu_da_lista_em` é a data da **coleta**, não a do fim do mandato.
5. **Sem disjuntor:** diferente da lápide (ADR 0026), marcar é reversível; uma lista íntegra mas curta marca gente como fora por uma coleta e a próxima carga boa corrige.
6. **Admin:** colunas e filtro `in_office`; continua só leitura.

## Alternativas
- **Apagar ou lápide:** descartada; sumir da lista de exercício não é retirada pela fonte (ADR 0022, 0026) e apagaria dado público legítimo.
- **Estado derivado na leitura** (comparar `ingestion_run` com a carga mais recente): descartada; custo a cada leitura e o perfil tem teste de "uma consulta só".
- **Nomes literais (`na_lista_de_exercicio`, `visto_por_ultimo_em`):** descartada por ora em favor de `em_exercicio` e `saiu_da_lista_em`, com a semântica documentada.
- **Disjuntor:** descartada; nada irreversível.
- **Distinguir o motivo da saída:** impossível com esta fonte.

## Consequências
- **Troca de legislatura (a 58, em 2027):** a lista passa a ser da legislatura nova, então todos os deputados da 57 saem da lista e ficam `em_exercicio: false`. É o comportamento correto para "em exercício", mas é um efeito grande e visível.
- `em_exercicio: false` pode ser só licença: quem consome a API não deve apresentar como "perdeu o mandato". Isso vale também para qualquer página futura, que depende do P-16 (ADR 0021, decisão 4).
- `saiu_da_lista_em` tem a resolução da frequência da coleta (24 h por padrão, ADR 0023).
- Duas normalizações simultâneas continuam sem trava (aviso antigo do código).
- Não trata histórico de mandatos nem de partido (fatia futura).
