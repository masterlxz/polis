# 0022: Deputados da Câmara numa tabela própria, fora de `Person`

**Data:** 2026-11-11

## Contexto
O ADR 0009 previa um modelo unificado "generalizado quando Câmara e Senado entrarem". A coleta bruta da lista de deputados está feita (ADR 0021, 513 linhas). Hoje `Person` é do TSE: a identidade é o ano do ciclo mais o `SQ_CANDIDATO`, e o código declara que ligar pessoas de ciclos diferentes não foi verificado. Um deputado tem identidade própria na Câmara (`id`) e nada prova, por si, que o candidato do TSE é o mesmo deputado (homônimos).

## Decisão
1. **App novo `apps/legislature`, modelo `Deputy`**, separado de `Person`. Nenhum vínculo entre os dois por enquanto.
2. **Chave única: (legislatura, id da Câmara).** Dentro da legislatura, troca de partido sobrescreve a linha; histórico de partido é fatia futura.
3. **Nunca apaga.** Quem some da lista continua na tabela; `ingestion_run` guarda a última execução que o viu, o que permite achá-lo.
4. **Normalização como a do TSE:** comando `normalize_camara`, sem rede, falha fechada (linha inválida ou conflito não gravam nada), mensagens só com nomes de coluna e contagens.
5. **Ligar deputado a pessoa do TSE é a fatia 4**, com revisão humana, porque um vínculo errado com aparência de certo é pior que nenhum.

## Alternativas
- **Generalizar `Person` (fonte e id de origem):** descartada por ora. Mexe na constraint, na busca, na API de perfil e nos testes do TSE, antes de existir prova de identidade entre as fontes.
- **`Deputy` em `apps/elections`:** descartada; mistura legislativo com eleições.
- **Chave só no id da Câmara:** descartada; a legislatura 58 sobrescreveria a 57 e o histórico de mandato se perderia.

## Consequências
- Por um tempo há duas "pessoas" no banco (candidato do TSE e deputado). A página e a busca de deputado são fatias futuras e nada vai a público antes do P-16 (ADR 0021, decisão 4).
- O ADR 0009 ("modelo unificado generalizado") fica adiado, não descartado: reavaliar depois da fatia 4, quando houver dado real sobre quando dois registros são a mesma pessoa.
- `siglaPartido` vazia é aceita (suposição, não medida); `siglaUf` e `nome` são obrigatórios. Se a Câmara devolver outra coisa, a normalização recusa e cita a coluna.
- `latest_run` e a base da normalização foram copiados do app de eleições para não acoplar os apps; a duplicação é candidata a refatoração depois.

## Atualização (2026-11-12, Sessão 65): saída do exercício
A decisão 3 segue (nunca apaga). A "saída do exercício" que ficou como fatia futura existe agora: `in_office` e `left_list_at` em `Deputy`, expostos na API interna como `em_exercicio` e `saiu_da_lista_em` (ADR 0027). A lápide do ADR 0026 continua só para o TSE.
