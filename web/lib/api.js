// Cliente da API interna do Django (ADR 0015, decisão 2). Só roda no servidor.
import { cache } from "react";

// Ciclo de 4 dígitos e SQ_CANDIDATO de 1 a 12 dígitos: o mesmo formato da rota do Django.
// O id da URL só segue para a API depois de casar aqui; o resto vira 404 sem chamar a API.
const PADRAO_DO_ID = /^\d{4}-\d{1,12}$/;
// Legislatura e id da Câmara, de 1 a 9 dígitos cada: o mesmo formato da rota do Django.
const PADRAO_DO_ID_DO_DEPUTADO = /^\d{1,9}-\d{1,9}$/;
const TEMPO_LIMITE_PADRAO_MS = 5000;

export function idValido(id) {
  return PADRAO_DO_ID.test(id);
}

export function idDeDeputadoValido(id) {
  return PADRAO_DO_ID_DO_DEPUTADO.test(id);
}

// A mensagem nunca leva o endereço da API nem o texto de erro dela.
export class ErroDaApi extends Error {}

function tempoLimiteMs() {
  const configurado = Number(process.env.API_TIMEOUT_MS);
  return configurado > 0 ? configurado : TEMPO_LIMITE_PADRAO_MS;
}

const MAX_CARACTERES_DA_CONSULTA = 100;

// O que o usuário digitou, pronto para ir à API: só o primeiro `q` se vier repetido, sem espaços
// nas pontas e cortado em 100 caracteres (a API corta de novo; aqui evita uma URL enorme).
// Vazio quer dizer "não busque".
export function prepararConsulta(valor) {
  const texto = Array.isArray(valor) ? valor[0] : valor;
  if (typeof texto !== "string") return "";
  return Array.from(texto.trim()).slice(0, MAX_CARACTERES_DA_CONSULTA).join("").trim();
}

// As 27 unidades da federação, as mesmas que a API aceita (`apps/elections/search.py`).
export const UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(
  " ",
);
const MAX_CARACTERES_DO_PARTIDO = 20; // tamanho do campo `party_acronym` na API

function primeiroTexto(valor) {
  const texto = Array.isArray(valor) ? valor[0] : valor;
  return typeof texto === "string" ? texto : "";
}

// A UF que vai à API: só uma das 27, em caixa alta. Qualquer outra coisa vira "" (sem filtro) para o
// `select` e a lista dizerem a mesma verdade na tela; a API, por sua vez, devolve vazio para UF
// inválida (contrato do PR #74), que é o que um cliente qualquer dela vê.
export function prepararUf(valor) {
  const uf = primeiroTexto(valor).trim().toUpperCase();
  return UFS.includes(uf) ? uf : "";
}

// A sigla do partido que vai à API: primeiro valor, sem espaços nas pontas, cortada em 20.
export function prepararPartido(valor) {
  return Array.from(primeiroTexto(valor).trim())
    .slice(0, MAX_CARACTERES_DO_PARTIDO)
    .join("")
    .trim();
}

function textoOuNulo(valor) {
  return valor === null || typeof valor === "string";
}

function resultadoValido(item) {
  return (
    typeof item?.nome === "string" &&
    typeof item.id === "string" &&
    idValido(item.id) &&
    Number.isInteger(item.ciclo) &&
    typeof item.aproximado === "boolean" &&
    textoOuNulo(item.uf) &&
    textoOuNulo(item.partido)
  );
}

// Busca pessoas pelo nome de urna (ADR 0016). O `id` de cada resultado vira `href`, então só
// passa se tiver o formato `<ciclo>-<sq>`; qualquer coisa fora do formato recusa a resposta toda.
export async function buscarPessoas(consulta, { uf = "", partido = "" } = {}) {
  let resposta;
  try {
    // Só o que está preenchido, sempre nesta ordem: sem filtro a chamada é a de antes dos filtros.
    const parametros = new URLSearchParams({ q: consulta });
    if (uf) parametros.set("uf", uf);
    if (partido) parametros.set("partido", partido);
    resposta = await fetch(`${process.env.API_URL}/internal/v1/busca/?${parametros}`, {
      cache: "no-store",
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(tempoLimiteMs()),
    });
  } catch {
    throw new ErroDaApi("falha ao falar com a API");
  }

  if (!resposta.ok) throw new ErroDaApi(`a API respondeu ${resposta.status}`);

  let corpo;
  try {
    corpo = await resposta.json();
  } catch {
    throw new ErroDaApi("a API devolveu algo que não é JSON");
  }
  if (!Array.isArray(corpo?.resultados) || !corpo.resultados.every(resultadoValido)) {
    throw new ErroDaApi("a API devolveu uma busca fora do formato esperado");
  }
  return corpo.resultados;
}

// `cache` do React: o título e a página pedem o mesmo perfil, mas a API é chamada uma vez só
// por requisição. O dado em si nunca fica em cache (`no-store`): quem a fonte retirar some na hora.
export const buscarPerfil = cache(async (id) => {
  if (!idValido(id)) return null;

  let resposta;
  try {
    resposta = await fetch(`${process.env.API_URL}/internal/v1/pessoas/${id}/`, {
      cache: "no-store",
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(tempoLimiteMs()),
    });
  } catch {
    throw new ErroDaApi("falha ao falar com a API");
  }

  if (resposta.status === 404) return null;
  if (!resposta.ok) throw new ErroDaApi(`a API respondeu ${resposta.status}`);

  let perfil;
  try {
    perfil = await resposta.json();
  } catch {
    throw new ErroDaApi("a API devolveu algo que não é JSON");
  }
  if (typeof perfil?.pessoa?.nome !== "string" || !Array.isArray(perfil.candidaturas)) {
    throw new ErroDaApi("a API devolveu um perfil fora do formato esperado");
  }
  return perfil;
});

function perfilDeDeputadoValido(perfil) {
  const { deputado, atribuicao } = perfil ?? {};
  return (
    typeof deputado?.nome === "string" &&
    Number.isInteger(deputado.legislatura) &&
    Number.isInteger(deputado.id_camara) &&
    textoOuNulo(deputado.partido) &&
    typeof deputado.uf === "string" &&
    typeof atribuicao?.fonte === "string" &&
    typeof atribuicao.conjunto === "string"
  );
}

// Código da votação do Senado, de 1 a 9 dígitos: o mesmo formato da rota do Django.
const PADRAO_DO_CODIGO_DA_VOTACAO = /^\d{1,9}$/;
// Página da lista: de 1 a 4 dígitos ASCII, como a API aceita (ADR 0030).
const PADRAO_DA_PAGINA = /^[0-9]{1,4}$/;

export function codigoDeVotacaoValido(codigo) {
  return PADRAO_DO_CODIGO_DA_VOTACAO.test(codigo);
}

// A página que vai à API: a que o usuário pediu, se válida; qualquer outra coisa vira a 1.
export function prepararPagina(valor) {
  const texto = primeiroTexto(valor);
  return PADRAO_DA_PAGINA.test(texto) && Number(texto) > 0 ? Number(texto) : 1;
}

// GET na API interna: `null` no 404; qualquer outra falha vira `ErroDaApi` sem o endereço.
async function lerDaApi(caminho) {
  let resposta;
  try {
    resposta = await fetch(`${process.env.API_URL}${caminho}`, {
      cache: "no-store",
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(tempoLimiteMs()),
    });
  } catch {
    throw new ErroDaApi("falha ao falar com a API");
  }
  if (resposta.status === 404) return null;
  if (!resposta.ok) throw new ErroDaApi(`a API respondeu ${resposta.status}`);
  try {
    return await resposta.json();
  } catch {
    throw new ErroDaApi("a API devolveu algo que não é JSON");
  }
}

function atribuicaoValida(atribuicao) {
  return typeof atribuicao?.fonte === "string" && typeof atribuicao.conjunto === "string";
}

function itemDaListaValido(item) {
  return (
    Number.isInteger(item?.codigo) &&
    typeof item.data === "string" &&
    typeof item.identificacao === "string" &&
    typeof item.ementa === "string" &&
    typeof item.resultado === "string" &&
    typeof item.secreta === "boolean"
  );
}

function listaDeVotacoesValida(corpo) {
  return (
    Array.isArray(corpo?.votacoes) &&
    corpo.votacoes.every(itemDaListaValido) &&
    Number.isInteger(corpo.pagina) &&
    Number.isInteger(corpo.total_paginas) &&
    (corpo.atribuicao === null || atribuicaoValida(corpo.atribuicao))
  );
}

// A lista nunca é 404 na API; se vier, é erro.
export async function buscarVotacoesDoSenado(pagina) {
  const corpo = await lerDaApi(`/internal/v1/senado/votacoes/?pagina=${pagina}`);
  if (!listaDeVotacoesValida(corpo)) {
    throw new ErroDaApi("a API devolveu uma lista de votações fora do formato esperado");
  }
  return corpo;
}

function votanteValido(item) {
  return (
    Number.isInteger(item?.id_senado) &&
    typeof item.nome === "string" &&
    textoOuNulo(item.partido) &&
    typeof item.uf === "string" &&
    typeof item.sigla === "string" &&
    typeof item.tem_perfil === "boolean"
  );
}

function contagemValida(contagem) {
  return (
    contagem !== null &&
    typeof contagem === "object" &&
    !Array.isArray(contagem) &&
    Object.values(contagem).every(Number.isInteger)
  );
}

function inteiroOuNulo(valor) {
  return valor === null || Number.isInteger(valor);
}

// A secreta só pode vir com `participacao` e a aberta só com `votos` (ADR 0030, decisão 2). O que
// misturar as formas é recusado inteiro: a página prefere quebrar a mostrar "Votou" como voto.
function detalheDeVotacaoValido(corpo) {
  const votacao = corpo?.votacao;
  if (typeof votacao?.secreta !== "boolean") return false;
  const chaveCerta = votacao.secreta ? "participacao" : "votos";
  const chaveErrada = votacao.secreta ? "votos" : "participacao";
  const totais = votacao.totais_da_fonte;
  return (
    Number.isInteger(votacao.codigo) &&
    typeof votacao.data === "string" &&
    typeof votacao.identificacao === "string" &&
    typeof votacao.ementa === "string" &&
    typeof votacao.resultado === "string" &&
    inteiroOuNulo(totais?.sim) &&
    inteiroOuNulo(totais.nao) &&
    inteiroOuNulo(totais.abstencao) &&
    !Object.hasOwn(corpo, chaveErrada) &&
    Array.isArray(corpo[chaveCerta]) &&
    corpo[chaveCerta].every(votanteValido) &&
    contagemValida(corpo.contagem_por_sigla) &&
    atribuicaoValida(corpo.atribuicao)
  );
}

// Mesmo desenho de `buscarPerfil`: uma chamada por requisição, nunca em cache de dado.
export const buscarVotacaoDoSenado = cache(async (codigo) => {
  if (!codigoDeVotacaoValido(codigo)) return null;
  const corpo = await lerDaApi(`/internal/v1/senado/votacoes/${codigo}/`);
  if (corpo === null) return null;
  if (!detalheDeVotacaoValido(corpo)) {
    throw new ErroDaApi("a API devolveu uma votação fora do formato esperado");
  }
  return corpo;
});

// Código do senador no Senado, de 1 a 9 dígitos: o mesmo formato da rota do Django.
export function codigoDeSenadorValido(codigo) {
  return PADRAO_DO_CODIGO_DA_VOTACAO.test(codigo);
}

function perfilDeSenadorValido(corpo) {
  const senador = corpo?.senador;
  return (
    Number.isInteger(senador?.id_senado) &&
    typeof senador.nome === "string" &&
    textoOuNulo(senador.partido) &&
    typeof senador.uf === "string" &&
    typeof senador.em_exercicio === "boolean" &&
    textoOuNulo(senador.saiu_da_lista_em) &&
    atribuicaoValida(corpo.atribuicao)
  );
}

// Mesmo desenho de `buscarVotacaoDoSenado`: uma chamada por requisição, nunca em cache de dado.
export const buscarSenador = cache(async (codigo) => {
  if (!codigoDeSenadorValido(codigo)) return null;
  const corpo = await lerDaApi(`/internal/v1/senadores/${codigo}/`);
  if (corpo === null) return null;
  if (!perfilDeSenadorValido(corpo)) {
    throw new ErroDaApi("a API devolveu um senador fora do formato esperado");
  }
  return corpo;
});

// Mesmo desenho de `buscarPerfil`: uma chamada por requisição, nunca em cache de dado.
export const buscarDeputado = cache(async (id) => {
  if (!idDeDeputadoValido(id)) return null;

  let resposta;
  try {
    resposta = await fetch(`${process.env.API_URL}/internal/v1/deputados/${id}/`, {
      cache: "no-store",
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(tempoLimiteMs()),
    });
  } catch {
    throw new ErroDaApi("falha ao falar com a API");
  }

  if (resposta.status === 404) return null;
  if (!resposta.ok) throw new ErroDaApi(`a API respondeu ${resposta.status}`);

  let perfil;
  try {
    perfil = await resposta.json();
  } catch {
    throw new ErroDaApi("a API devolveu algo que não é JSON");
  }
  if (!perfilDeDeputadoValido(perfil)) {
    throw new ErroDaApi("a API devolveu um perfil fora do formato esperado");
  }
  return perfil;
});
