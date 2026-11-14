# 0030: API interna das votações do Senado: secreta como `participacao` e contagem calculada

**Data:** 2026-11-13

## Contexto
As votações do Senado (ADR 0029) estão no banco com dado real (Sessão 70: 87 votações, 7.047 votos), mas nada as lê. O front precisa de uma API interna (ADR 0015, decisão 2) antes da página. Dois fatos da fonte pesam no formato: nas **40 votações secretas** cada senador vem com `Votou` (participação, não posição; ADR 0029, decisão 6), e nas **47 abertas os totais da fonte são nulos**.

## Decisão
1. **Duas rotas de leitura** em `apps/legislature`: `GET /internal/v1/senado/votacoes/` (lista) e `GET /internal/v1/senado/votacoes/<codigo>/` (detalhe, código de 1 a 9 dígitos; o resto é 404 sem banco). Resposta montada campo a campo, com a atribuição da fonte, como as APIs do deputado e do senador. Não é a API pública do ADR 0013.
2. **Na votação secreta a lista sai com outra chave**: `participacao` em vez de `votos`, nunca as duas. Um cliente que não leu este ADR não consegue somar `Votou` como posição: o erro vira chave ausente, não dado errado em silêncio.
3. **`contagem_por_sigla` é calculada pelo polis** a partir dos itens, separada de `totais_da_fonte` (como vieram; nulos nas abertas). Nada é gravado: o ADR 0029, decisão 6, continua valendo.
4. **Lista com 50 por página**, da mais recente para a mais antiga (data, depois código). `?pagina=` de 1 a 4 dígitos ASCII; malformada ou 0 dá 400; além da última dá 200 com a lista vazia (decisão do dono). A atribuição da lista é a da coleta mais recente entre as votações da página (nula se a página vier vazia).
5. Siglas de voto, `resultado` (`A`/`R`) e `S/Partido` saem como vêm; partido vazio sai nulo. O significado das siglas segue sem verificação; tratar na página.
6. **Emenda (Sessão 73): `tem_perfil` em cada item de `votos`/`participacao`.** Booleano: o código do parlamentar existe em `Senator` (junção por código na leitura, ADR 0029, decisão 5). Existir não quer dizer estar em exercício: quem saiu da lista tem perfil com `em_exercicio` falso. O front liga o nome ao perfil só quando é verdadeiro (12 de 93 códigos do ano não estão em `Senator`). Custo: o detalhe passa a 3 consultas (uma a mais, para os códigos com perfil, sem N+1), fixadas por teste. Campo acrescentado, nenhum removido.

## Alternativas
- **Secreta só com os totais, sem lista:** descartada pelo dono; perde a presença, que a fonte publica.
- **Mesma forma com a marca `secreta`:** descartada pelo dono; depende de todo cliente ler a marca, o risco que o ADR 0029 quer evitar.
- **Só os totais da fonte, sem contagem:** descartada pelo dono; a página teria de contar no front.
- **Página além da última como 404:** descartada pelo dono; 200 vazio é previsível para quem percorre as páginas num laço.

## Consequências
- O cliente trata duas formas no detalhe (`votos` ou `participacao`). É o custo de a forma errada não existir.
- Detalhe em 3 consultas desde a emenda da decisão 6 (votação com execução, conjunto e fonte num JOIN; os votos; os códigos com perfil), lista em 2 (contagem e página), fixadas por teste.
- Se `contagem_por_sigla` e `totais_da_fonte` divergirem numa secreta, a divergência aparece; não é escondida.
- Reversível: só leitura, sem migração. Mudar o formato depois custa a API e a página.
- **Não validado por mim:** o significado das siglas; o uso real pela página (fatia seguinte); nada vai a público antes do P-16.
