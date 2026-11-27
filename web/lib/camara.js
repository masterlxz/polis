// Como as páginas das votações da Câmara mostram o que a fonte manda (ADR 0031 e 0032). A API
// devolve `aprovacao` e as siglas de voto como a fonte as manda, e as páginas as mostram assim, com
// a legenda do que a documentação oficial da Câmara diz (ADR 0032, emenda 2; lida em 2026-11-26).
import { dataBr } from "./formatar.js";

export const ROTULO_DA_APROVACAO = "Aprovação (código da fonte)";

export const URL_DA_DOCUMENTACAO =
  "https://dadosabertos.camara.leg.br/howtouse/2020-02-07-dados-votacoes.html";

export const PREFIXO_DA_NOTA = "Códigos como a fonte os manda.";

// `aprovacao`: 1 "resultou em aprovação"; 0 "não foi aprovada" (rejeitada ou sem quórum); vazio
// quando não é possível afirmar o resultado sem leitura humana da descrição.
export const LEGENDA_DA_APROVACAO =
  "Aprovação, segundo a documentação da Câmara: 1 é votação que resultou em aprovação; 0, proposição não aprovada (rejeitada ou sem quórum); sem código, a Câmara não afirma o resultado.";

// Só o que a documentação descreve (em `votosOutros`); ela não lista todos os valores de voto.
export const LEGENDA_DAS_SIGLAS =
  "Votos: Abstenção, Obstrução (o parlamentar se abstém e não quer ser contado no quórum) e Artigo 17 (abstenção obrigatória do presidente, em referência ao Regimento da Câmara) entram em “outros” nos totais da Câmara.";

// O texto da nota com as legendas que a página precisa (a da aprovação, a das siglas ou as duas);
// `null` se não precisa de nenhuma.
export function textoDaNota({ aprovacao, siglas }) {
  if (!aprovacao && !siglas) return null;
  return [PREFIXO_DA_NOTA, aprovacao && LEGENDA_DA_APROVACAO, siglas && LEGENDA_DAS_SIGLAS]
    .filter(Boolean)
    .join(" ");
}

// `voto` nulo é a ausência de posição na fonte (a Câmara publica a presença sem o voto).
export const SEM_POSICAO = "Sem posição registrada";

// Só o que os dados coletados mostram: os votos vêm de outro conjunto (`votos-2026`), e a fonte pode
// ter publicado o placar e não os votos, ou o contrário.
export const SEM_LISTA_NOMINAL =
  "Esta votação não tem lista de votos nominais nos dados coletados.";

// Frase de fato, sem causa: o significado do zero na fonte não foi verificado (ADR 0031 e 0032).
export const TOTAIS_ZERADOS = "Os totais da fonte estão zerados e não são mostrados.";

// Ementa com mais de 300 caracteres sai recolhida (decisão do dono, 2026-11-27): a medição do ADR 0033
// chega a 5.259 caracteres, e uma votação com dezenas de proposições viraria um muro de texto.
export const LIMITE_DA_EMENTA = 300;

// O resumo de uma ementa longa (os 300 primeiros caracteres, sem espaço no fim, e "…"), ou `null` se
// ela cabe inteira. Conta por ponto de código: `slice` contaria unidades UTF-16 e poderia partir um
// caractere fora do BMP ao meio.
export function resumoDaEmenta(ementa) {
  const caracteres = [...ementa];
  if (caracteres.length <= LIMITE_DA_EMENTA) return null;
  return `${caracteres.slice(0, LIMITE_DA_EMENTA - 1).join("").trimEnd()}…`;
}

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
