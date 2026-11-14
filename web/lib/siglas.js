// Como a página mostra as siglas das votações do Senado (ADR 0029 e 0030). A API devolve a sigla
// crua; o significado é afirmação editorial do polis, com fonte: a Rodada 4 de
// `project/fontes/senado.md` (2026-11-13), onde cada sigla abaixo veio sempre com a mesma
// `descricaoVotoParlamentar` da própria fonte. Sigla fora daqui aparece crua, com nota.

// Texto da fonte, como veio em `descricaoVotoParlamentar`.
const LEGENDA = {
  AP: "Atividade parlamentar",
  LAP: "Licença paternidade ou ao adotante",
  LP: "Licença Particular",
  LS: "Licença saúde",
  MIS: "Missão da Casa no País/exterior",
  NA: "Dispositivo não citado",
  NCom: "Não Compareceu",
  "P-NRV": "Presente – Não registrou voto",
};

// Siglas cujo texto já é a descrição (a fonte as manda sem descrição).
const POR_EXTENSO = new Set(["Sim", "Não", "Abstenção", "Presidente (art. 51 RISF)"]);

// `Votou` só existe na votação secreta: diz que votou, não como (ADR 0029, decisão 6).
const VOTOU = "Votou";

export function siglaConhecida(sigla) {
  return sigla === VOTOU || POR_EXTENSO.has(sigla) || Object.hasOwn(LEGENDA, sigla);
}

// "AP" vira "Atividade parlamentar (AP)"; "Votou" vira "Votou (voto secreto)"; sigla desconhecida
// volta como veio (quem chama mostra a nota).
export function descreverSigla(sigla) {
  if (sigla === VOTOU) return "Votou (voto secreto)";
  if (Object.hasOwn(LEGENDA, sigla)) return `${LEGENDA[sigla]} (${sigla})`;
  return sigla;
}

// A fonte escreve "sem partido" como o texto literal `S/Partido`; nulo vira vazio.
export function partidoParaExibir(partido) {
  if (partido === "S/Partido") return "Sem partido";
  return partido ?? "";
}

// A/R não têm descrição na fonte. A leitura é do placar (82 de 82 e 5 de 5 na Rodada 4), por isso
// sai com `inferido: true` e a página mostra a nota. Letra desconhecida volta crua.
const RESULTADOS = { A: "Aprovada", R: "Rejeitada" };

export function resultadoParaExibir(letra) {
  if (Object.hasOwn(RESULTADOS, letra)) {
    return { curto: RESULTADOS[letra], completo: `${RESULTADOS[letra]} (${letra})`, inferido: true };
  }
  return { curto: letra, completo: letra, inferido: false };
}

export const NOTA_DO_RESULTADO =
  "O Senado informa só a letra; o polis a lê pelo placar, que coincidiu em todas as 87 votações medidas.";

export const NOTA_DA_SIGLA =
  "Há sigla do Senado nesta votação que aparece como veio: o polis ainda não verificou o significado dela.";
