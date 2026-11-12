# 0026: Retirada pela fonte e lápide (TSE), com disjuntor

**Data:** 2026-11-12

## Contexto
O ADR 0005 (decisão 9) manda: registro ausente de um arquivo **íntegro** vira "retirado pela fonte": some da interface e da API, os campos pessoais são apagados (banco e camada bruta) e fica uma lápide (id de origem, fonte, data); após um restore de backup, as lápides são reaplicadas antes de qualquer exposição pública. Até aqui a normalização nunca apagava. Esta fatia implementa a decisão, o que **apaga dado pessoal de forma irreversível** (AGENTS §4).

## Decisão
1. **Só o TSE** (`tse/consulta-cand-2026`). Deputado da Câmara segue "nunca apaga" (ADR 0022): sumir da lista de deputados **em exercício** é fim de mandato ou licença, não a Câmara retirando o registro. A "saída do exercício" fica como fatia própria, sem apagar nada.
2. **Detecção sem estado novo:** a candidatura já normalizada que não está na carga é retirada. É a mesma ideia do `normalize_latest` ao contrário: o upsert carimba `ingestion_run` em tudo que está no arquivo. Só uma execução `succeeded` com linhas chega à normalização; falha técnica e "arquivo igual" (0 linhas) nunca apagam.
3. **O que se apaga:** a candidatura; a pessoa, se era a última candidatura dela (a eleição fica: não é dado pessoal); e as linhas brutas do id em todas as cargas retidas (por varredura, sem depender do formato do valor).
4. **Lápide (`Tombstone`, em `apps/sources`):** `dataset`, `source_key` (`ano:SQ_CANDIDATO:CD_ELEICAO:turno`), `retired_at`, `retired_in_run` e `reinstated_at`. Só ids e datas, **nenhum dado pessoal**; um teste trava a lista de campos. Única por (conjunto, chave). Só leitura no admin.
5. **Disjuntor:** se as retiradas de uma carga passam de `max(20, 1% das candidaturas já normalizadas)`, a normalização **inteira** é recusada (nada gravado nem apagado, o bruto fica, o comando sai com erro, mensagem só com contagens). `normalize_tse --aceitar-retiradas` libera. O agendador (`normalize_latest`) nunca passa a flag. O plano roda **antes** de qualquer gravação, na mesma transação do upsert.
6. **Reaparecimento segue a fonte:** o registro volta com a carga e a lápide fica com `reinstated_at`; lápide reativada não vale na reaplicação. Se sumir de novo, a mesma lápide volta a ser ativa (nova execução, nova data). É o ADR 0005, decisão 10: o polis segue o que a fonte fizer.
7. **Reaplicação após restore:** comando `apply_tombstones` (sem rede, idempotente) apaga de novo o que as lápides ativas cobrem e voltou por um backup antigo. Roda **depois do restore e antes de subir o `web`** (runbook).

## Alternativas
- **Lápide também para o deputado:** descartada; trataria fim de mandato como retirada e apagaria dado público legítimo (ADR 0022).
- **Sem disjuntor:** descartada; um arquivo "íntegro" (hash e esquema ok) mas incompleto apagaria a base, e apagar não tem volta.
- **Bloquear o reaparecimento até revisão humana:** descartada; exige comando e decisão manual a cada caso, e contradiz seguir a fonte.
- **Marcar a retirada com estado novo (flag no registro) em vez de comparar com a carga:** descartada; o carimbo `ingestion_run` já dá a informação.
- **`__in` do JSON para achar o bruto:** descartada em favor de varredura; um valor com formato diferente deixaria dado pessoal para trás.

## Consequências
- **Limite do disjuntor não medido** (1%, mínimo 20): é escolha minha; só há um dia de dados do TSE. Retiradas legítimas acima do limite exigem o comando manual.
- A varredura do bruto custa uma passada nas cargas retidas (até ~126 mil linhas) quando há retirada; **tempo não medido**.
- Um backup restaurado traz as lápides só até a data do backup; retiradas posteriores são detectadas de novo na próxima coleta. Entre o restore e o `apply_tombstones` o dado retirado existe no banco: por isso a ordem do runbook (sem `web` no ar) é parte da segurança.
- Duas normalizações simultâneas continuam sem trava (aviso antigo do código).
- O teste antigo "candidatura que sumiu continua no banco" mudou de propósito (agora é retirada).
- Não resolve o P-16 (pedidos de remoção por LGPD) nem mostra lápide ao público.
