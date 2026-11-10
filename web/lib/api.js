// Cliente da API interna do Django (ADR 0015, decisão 2). Só roda no servidor.
import { cache } from "react";

// Ciclo de 4 dígitos e SQ_CANDIDATO de 1 a 12 dígitos: o mesmo formato da rota do Django.
// O id da URL só segue para a API depois de casar aqui; o resto vira 404 sem chamar a API.
const PADRAO_DO_ID = /^\d{4}-\d{1,12}$/;
const TEMPO_LIMITE_PADRAO_MS = 5000;

export function idValido(id) {
  return PADRAO_DO_ID.test(id);
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
export async function buscarPessoas(consulta) {
  let resposta;
  try {
    const parametros = new URLSearchParams({ q: consulta });
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
