# 0023: Agendador da coleta: comando chamado de fora, estado no banco

**Data:** 2026-11-11

## Contexto
O ADR 0008 (decisão 6) fixou as regras de agendamento (minuto aleatório, nunca horário redondo; Câmara depois das 08:00 GMT; TSE por SHA-256), mas "fila e agendamento" ficaram em aberto (ADR 0006) e toda coleta era manual (`ingest_dataset`). Não há ainda Compose de produção (ADR 0011: um VPS com Docker Compose).

## Decisão
1. **Mecanismo:** o comando `collect_due` coleta os conjuntos vencidos e termina. Um cron ou timer **fora do repositório** o chama **a cada minuto** (`* * * * *`): o minuto sorteado só vale nesse ritmo, porque num disparo mais espaçado a coleta cai no minuto do disparo.
2. **Estado no banco:** `Dataset.schedule_interval_hours` (vazio = não agendado), `earliest_hour_utc` (0 a 23) e `next_collection_at`. O dono muda tudo no admin; para forçar uma coleta, põe uma data passada. O `seed_sources` só preenche na criação (TSE: 24 h, janela 0; Câmara: 24 h, janela 8) e nunca sobrescreve.
3. **Sorteio:** a próxima coleta mantém a hora do dia e muda só o minuto, entre 1 e 59 e nunca múltiplo de 5; antes da janela, sobe para a hora da janela. Conjunto nunca armado não coleta: sorteia a primeira data.
4. **Reserva atômica:** antes de coletar, um `UPDATE ... WHERE next_collection_at = <valor lido>`; quem perde a corrida pula o conjunto. Não segura transação durante a rede.
5. **Falhas:** execução `failed`, portão recusado, erro inesperado e processo que morre no meio voltam a tentar em **6 h** (constante `RETRY_HOURS`). Só o erro inesperado faz o comando terminar com erro, para o cron avisar. Bloqueio já pausa a fonte (ADR 0008, decisão 5).
6. **Um cliente HTTP por invocação**, compartilhado: a pausa de 3 s por host e o bloqueio valem entre os conjuntos.
7. **Só coleta.** A normalização depois da coleta é uma fatia própria.

## Alternativas
- **Celery, RQ ou Django-Q com broker:** descartadas; dependência, broker e serviço a mais num VPS de cerca de US$ 20 (ADR 0011), para dois conjuntos.
- **Processo residente (APScheduler):** descartada; estado em memória e risco de rodar duplicado.
- **Configuração em constantes do catálogo:** descartada; o minuto sorteado não ficaria gravado e mudar o intervalo exigiria deploy.
- **`SELECT FOR UPDATE` ou trava de sessão:** descartadas; segurariam transação ou conexão durante a rede.
- **Recuo escalonado nas falhas:** adiado; 6 h fixas bastam enquanto a falha é visível no admin.

## Consequências
- Quem opera o servidor precisa instalar o disparo de 1 minuto (cron ou timer); sem ele nada coleta, e a falta não é detectada por nada ainda (monitoramento é futuro, PRD §12).
- A reserva protege o agendador de si mesmo; uma coleta manual (`ingest_dataset`) ao mesmo tempo continua possível.
- O padrão de 24 h para o TSE e a janela de 08:00 GMT para a Câmara vêm de medições de um dia só (`fontes/tse.md`, `fontes/camara.md`); reconferir.
- Constante de 6 h e padrão de 24 h são escolhas minhas, não medidas.
