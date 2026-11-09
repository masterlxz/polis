// Página de candidato (`/pessoas/<ciclo>-<sq>/`, ADR 0015 e ADR 0014), contra o servidor de
// produção e uma API falsa. Dados todos sintéticos. O que mais importa: o que sai na tela é só
// o que a página conhece, link vindo da fonte só se for http(s), e a falha da API não vaza.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

const ID = "2026-40002532272";
const CAMINHO_DA_API = `GET /internal/v1/pessoas/${ID}/`;

let api;
let front;

before(async () => {
  api = await iniciarApiFalsa();
  front = await iniciarNext({ apiUrl: api.url });
});

after(() => {
  front?.parar();
  api?.parar();
});

function candidatura(extra = {}) {
  return {
    eleicao: {
      codigo: 6259,
      turno: 1,
      ano: 2026,
      descricao: "Eleições Gerais Estaduais 2026",
      data: "2026-10-04",
    },
    cargo: "GOVERNADOR",
    abrangencia: "ESTADUAL",
    uf: "AM",
    unidade_eleitoral: { codigo: "AM", nome: "AMAZONAS" },
    numero_urna: 55,
    partido: { numero: 55, sigla: "PSD", nome: "PARTIDO DE TESTE" },
    federacao: null,
    coligacao: null,
    situacao: null,
    resultado: null,
    atribuicao: {
      fonte: "TSE: Portal de Dados Abertos",
      conjunto: "Consulta de candidatos 2026",
      coletado_em: "2026-11-08T02:17:57.965558+00:00",
      gerado_pela_fonte_em: "2026-03-03T11:11:11+00:00",
      url_origem: "https://dados.example.org/consulta_cand_2026.zip",
      licenca: { id: "cc-by", url: "https://licencas.example.org/cc-by" },
    },
    ...extra,
  };
}

function perfil({ nome = "FULANO DE TESTE", candidaturas = [candidatura()], ...extra } = {}) {
  return {
    pessoa: { ciclo: 2026, id_tse: 40002532272, nome },
    candidaturas,
    ...extra,
  };
}

async function pagina(id = ID, resposta = { status: 200, corpo: perfil() }) {
  api.resposta = () => resposta;
  const retorno = await fetch(`${front.base}/pessoas/${id}/`);
  return { status: retorno.status, html: await retorno.text() };
}

test("pessoa com uma candidatura: nome, cargo, UF, partido e número de urna", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200);
  assert.match(html, /<h1[^>]*>FULANO DE TESTE<\/h1>/);
  for (const trecho of ["GOVERNADOR", "AM", "AMAZONAS", "55", "PSD", "PARTIDO DE TESTE"]) {
    assert.ok(html.includes(trecho), `faltou "${trecho}" no HTML`);
  }
});

test("duas candidaturas viram duas seções h2, a do 1º turno primeiro", async () => {
  const segunda = candidatura({
    eleicao: {
      codigo: 6260,
      turno: 2,
      ano: 2026,
      descricao: "Eleições Gerais Estaduais 2026",
      data: "2026-10-25",
    },
  });
  const { html } = await pagina(ID, {
    status: 200,
    corpo: perfil({ candidaturas: [candidatura(), segunda] }),
  });

  assert.equal((html.match(/<h2[ >]/g) ?? []).length, 2);
  assert.ok(html.indexOf("1º turno") !== -1, "faltou o 1º turno");
  assert.ok(html.indexOf("1º turno") < html.indexOf("2º turno"), "ordem dos turnos errada");
});

test("atribuição: fonte, conjunto, coleta em horário de Brasília, link do original e licença", async () => {
  const { html } = await pagina();

  assert.ok(html.includes("TSE: Portal de Dados Abertos"));
  assert.ok(html.includes("Consulta de candidatos 2026"));
  // 2026-11-08T02:17Z é 07/11/2026 23:17 em Brasília.
  assert.match(html, /07\/11\/2026[^<]*23:17/);
  assert.ok(html.includes('href="https://dados.example.org/consulta_cand_2026.zip"'));
  assert.ok(html.includes("cc-by"));
  assert.ok(html.includes('href="https://licencas.example.org/cc-by"'));
});

test("a data de geração pela fonte não aparece (fuso do TSE não verificado)", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  assert.ok(!controle.html.includes("11:11:11"));
  assert.ok(!controle.html.includes("03/03/2026"));
});

for (const perigoso of [
  "javascript:alert(1)",
  "data:text/html,<b>x</b>",
  "ftp://dados.example.org/x",
  "//evil.example.org/x",
  "vbscript:x",
]) {
  test(`link da fonte que não é http(s) vira texto, sem href: ${perigoso}`, async () => {
    const atribuicao = {
      ...candidatura().atribuicao,
      url_origem: perigoso,
      licenca: { id: "cc-by", url: perigoso },
    };
    const { status, html } = await pagina(ID, {
      status: 200,
      corpo: perfil({ candidaturas: [candidatura({ atribuicao })] }),
    });

    assert.equal(status, 200, "controle: a página precisa existir");
    assert.ok(!/href="(javascript|data|vbscript|ftp|\/\/)/i.test(html), "virou href");
  });
}

test("nome com HTML aparece escapado, sem tag ativa", async () => {
  const { status, html } = await pagina(ID, {
    status: 200,
    corpo: perfil({ nome: "<script>alert(1)</script>" }),
  });

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("<script>alert(1)</script>"));
  assert.ok(html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));
});

test("federação, coligação e situação nulas somem da página", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200, "controle: a página precisa existir");
  for (const rotulo of ["Federação", "Coligação", "Situação", "Resultado"]) {
    assert.ok(!html.includes(rotulo), `"${rotulo}" não deveria aparecer`);
  }
  assert.ok(!html.includes(">null<"));
  assert.ok(!html.includes("—"));
});

test("federação, coligação, situação e resultado preenchidos aparecem", async () => {
  const cheia = candidatura({
    federacao: { sigla: "FED", nome: "FEDERAÇÃO DE TESTE" },
    coligacao: { nome: "COLIGAÇÃO DE TESTE", composicao: "A / B / C" },
    situacao: "DEFERIDO",
    resultado: "ELEITO",
  });
  const { html } = await pagina(ID, {
    status: 200,
    corpo: perfil({ candidaturas: [cheia] }),
  });

  for (const trecho of [
    "Federação",
    "FEDERAÇÃO DE TESTE",
    "Coligação",
    "COLIGAÇÃO DE TESTE",
    "A / B / C",
    "Situação",
    "DEFERIDO",
    "Resultado",
    "ELEITO",
  ]) {
    assert.ok(html.includes(trecho), `faltou "${trecho}" no HTML`);
  }
});

test("chave desconhecida que a API devolva não chega ao HTML", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  const { html } = await pagina(ID, {
    status: 200,
    corpo: perfil({
      nome_social: "SEGREDO-DO-NOME-SOCIAL",
      pessoa_extra: "SEGREDO-EXTRA",
      candidaturas: [candidatura({ campo_novo: "SEGREDO-NA-CANDIDATURA" })],
    }),
  });

  assert.ok(!html.includes("SEGREDO"));
});

test("API responde 404: página 404 em português", async () => {
  const { status, html } = await pagina(ID, { status: 404, corpo: { erro: "não encontrado" } });

  assert.equal(status, 404);
  assert.match(html, /não encontrad/i);
  assert.ok(api.chamadas.includes(CAMINHO_DA_API), "a API não foi chamada");
});

test("API responde 500: erro genérico, sem o endereço da API", async () => {
  const { status, html } = await pagina(ID, { status: 500, corpo: { erro: "boom" } });

  assert.equal(status, 500);
  assert.ok(api.chamadas.includes(CAMINHO_DA_API), "a API não foi chamada");
  assert.ok(!html.includes(api.url));
  assert.ok(!html.includes(new URL(api.url).host));
});

test("API fora do ar: erro 500 sem o endereço da API", async () => {
  const porta = api.url.split(":").pop();
  const parado = await iniciarNext({ apiUrl: "http://127.0.0.1:9" });
  try {
    const controle = await fetch(`${parado.base}/saude/`);
    assert.equal(controle.status, 200, "controle: o front precisa estar no ar");

    const resposta = await fetch(`${parado.base}/pessoas/${ID}/`);
    const html = await resposta.text();

    assert.equal(resposta.status, 500);
    assert.ok(!html.includes("127.0.0.1:9"));
    assert.ok(!html.includes(porta));
  } finally {
    parado.parar();
  }
});

test("API que não responde estoura o tempo limite e dá erro 500", async () => {
  const lento = await iniciarNext({ apiUrl: api.url, env: { API_TIMEOUT_MS: "400" } });
  try {
    api.resposta = () => ({ travar: true });
    const antes = Date.now();

    const resposta = await fetch(`${lento.base}/pessoas/${ID}/`);

    assert.equal(resposta.status, 500);
    assert.ok(Date.now() - antes < 10_000, "não respeitou o tempo limite");
  } finally {
    lento.parar();
  }
});

for (const invalido of ["2026-abc", "20261", "2026-1000000000001", "2026-", "abcd-123"]) {
  test(`id malformado dá 404 sem chamar a API: ${invalido}`, async () => {
    const controle = await pagina();
    assert.equal(controle.status, 200, "controle: a página precisa existir");
    const antes = api.chamadas.length;

    const { status } = await pagina(invalido);

    assert.equal(status, 404);
    assert.equal(api.chamadas.length, antes, "chamou a API com um id inválido");
  });
}

test("id válido: a API recebe exatamente GET /internal/v1/pessoas/<id>/", async () => {
  api.chamadas.length = 0;

  await pagina();

  assert.deepEqual(api.chamadas, [CAMINHO_DA_API]);
});

test("estrutura: idioma pt-BR, um h1, título com o descritor e noindex", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.match(html, /<html[^>]*lang="pt-BR"/);
  assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1);
  assert.match(html, /<title>[^<]*transparência e inteligência cívica[^<]*<\/title>/);
  assert.match(html, /<meta name="robots" content="noindex/);
});
