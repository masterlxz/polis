// Como as páginas das votações da Câmara mostram o que a fonte manda (ADR 0031 e 0032). A API
// devolve `aprovacao` e as siglas de voto como a fonte as manda; o significado delas não foi
// verificado, então nada aqui as traduz.
import { dataBr } from "./formatar.js";

export const ROTULO_DA_APROVACAO = "Aprovação (código da fonte)";

export const NOTA_DO_CODIGO =
  "Códigos como a fonte os manda; o significado de 1/0 e das siglas de voto não foi verificado.";

// `voto` nulo é a ausência de posição na fonte (a Câmara publica a presença sem o voto).
export const SEM_POSICAO = "Sem posição registrada";

// Só o que os dados coletados mostram: os votos vêm de outro conjunto (`votos-2026`), e a fonte pode
// ter publicado o placar e não os votos, ou o contrário.
export const SEM_LISTA_NOMINAL =
  "Esta votação não tem lista de votos nominais nos dados coletados.";

// Frase de fato, sem causa: o significado do zero na fonte não foi verificado (ADR 0031 e 0032).
export const TOTAIS_ZERADOS = "Os totais da fonte estão zerados e não são mostrados.";

// "24/11/2026 · PLEN": a Câmara não tem uma identificação curta como a do Senado.
export function tituloDaVotacao(votacao) {
  return `${dataBr(votacao.data) ?? votacao.data} · ${votacao.orgao}`;
}

// Os totais da fonte como linhas da tabela, ou `null` se são `0/0/0`: em 8.984 das 9.153 votações
// medidas a fonte manda zeros porque não publicou o placar, e zero ali não é uma contagem (ADR 0032,
// decisão 3). Mostrar "Sim 0, Não 0" afirmaria um resultado que a fonte não deu.
export function totaisInformados(totais) {
  if (totais.sim + totais.nao + totais.outros === 0) return null;
  return [
    ["Sim", totais.sim],
    ["Não", totais.nao],
    ["Outros", totais.outros],
  ];
}
