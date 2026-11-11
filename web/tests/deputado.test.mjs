// Página do deputado (`/deputados/<legislatura>-<id>/`, ADR 0015, ADR 0021 decisão 4), contra o
// servidor de produção e uma API falsa. Dados todos sintéticos. O que mais importa: o que sai na
// tela é só o que a página conhece, link vindo da fonte só se for http(s), a Câmara aparece sem
// licença inventada e a falha da API não vaza.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

const ID = "57-204554";
const CAMINHO_DA_API = `GET /internal/v1/deputados/${ID}/`;

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

function atribuicaoPadrao(extra = {}) {
  return {
    fonte: "Câmara dos Deputados: Dados Abertos",
    conjunto: "Deputados em exercício (legislatura atual)",
    coletado_em: "2026-11-10T15:30:00+00:00",
    url_origem: "https://dados.example.org/api/v2/deputados?itens=100",
    licenca: { id: null, url: null },
    ...extra,
  };
}

function perfil({ nome = "ANA DA CÂMARA", partido = "XYZ", atribuicao, ...extra } = {}) {
  return {
    deputado: { legislatura: 57, id_camara: 204554, nome, partido, uf: "SP" },
    atribuicao: atribuicao ?? atribuicaoPadrao(),
    ...extra,
  };
}

async function pagina(id = ID, resposta = { status: 200, corpo: perfil() }) {
  api.resposta = () => resposta;
  const retorno = await fetch(`${front.base}/deputados/${id}/`);
  return { status: retorno.status, html: await retorno.text() };
}

test("deputado: nome, partido, UF e legislatura", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200);
  assert.match(html, /<h1[^>]*>ANA DA CÂMARA<\/h1>/);
  for (const trecho of ["XYZ", "SP", "57", "204554"]) {
    assert.ok(html.includes(trecho), `faltou "${trecho}" no HTML`);
  }
});

test("partido nulo some da página: nada de rótulo vazio nem 'null'", async () => {
  const controle = await pagina();
  assert.ok(controle.html.includes("Partido"), "controle: com partido o rótulo aparece");

  const { status, html } = await pagina(ID, { status: 200, corpo: perfil({ partido: null }) });

  assert.equal(status, 200);
  assert.ok(!html.includes("Partido"));
  assert.ok(!html.includes(">null<"));
});

test("atribuição: fonte, conjunto, coleta em horário de Brasília e link do original", async () => {
  const { html } = await pagina();

  assert.ok(html.includes("Câmara dos Deputados: Dados Abertos"));
  assert.ok(html.includes("Deputados em exercício (legislatura atual)"));
  // 2026-11-10T15:30Z é 10/11/2026 12:30 em Brasília.
  assert.match(html, /10\/11\/2026[^<]*12:30/);
  assert.ok(html.includes('href="https://dados.example.org/api/v2/deputados?itens=100"'));
});

test("sem licença declarada, a página não mostra licença nem inventa uma", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  assert.ok(!controle.html.includes("Licença"));
  assert.ok(!/cc-by/i.test(controle.html));
});

test("licença que a API informe aparece (a página não presume que é sempre nula)", async () => {
  const atribuicao = atribuicaoPadrao({
    licenca: { id: "cc-by", url: "https://licencas.example.org/cc-by" },
  });

  const { html } = await pagina(ID, { status: 200, corpo: perfil({ atribuicao }) });

  assert.ok(html.includes("Licença"));
  assert.ok(html.includes('href="https://licencas.example.org/cc-by"'));
});

for (const perigoso of [
  "javascript:alert(1)",
  "data:text/html,<b>x</b>",
  "ftp://dados.example.org/x",
  "//evil.example.org/x",
  "vbscript:x",
]) {
  test(`link da fonte que não é http(s) vira texto, sem href: ${perigoso}`, async () => {
    const atribuicao = atribuicaoPadrao({ url_origem: perigoso });
    const { status, html } = await pagina(ID, { status: 200, corpo: perfil({ atribuicao }) });

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

test("chave desconhecida que a API devolva não chega ao HTML", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  const corpo = perfil({ campo_extra: "SEGREDO-NA-RAIZ" });
  corpo.deputado.email = "SEGREDO-NO-DEPUTADO";
  corpo.atribuicao.interno = "SEGREDO-NA-ATRIBUICAO";
  const { html } = await pagina(ID, { status: 200, corpo });

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

test("resposta fora do formato esperado: erro 500 genérico, sem o texto da resposta", async () => {
  const { status, html } = await pagina(ID, {
    status: 200,
    corpo: { deputado: { nome: 42 }, atribuicao: "SEGREDO-FORA-DO-FORMATO" },
  });

  assert.equal(status, 500);
  assert.ok(!html.includes("SEGREDO"));
});

test("API fora do ar: erro 500 sem o endereço da API", async () => {
  const porta = api.url.split(":").pop();
  const parado = await iniciarNext({ apiUrl: "http://127.0.0.1:9" });
  try {
    const controle = await fetch(`${parado.base}/saude/`);
    assert.equal(controle.status, 200, "controle: o front precisa estar no ar");

    const resposta = await fetch(`${parado.base}/deputados/${ID}/`);
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

    const resposta = await fetch(`${lento.base}/deputados/${ID}/`);

    assert.equal(resposta.status, 500);
    assert.ok(Date.now() - antes < 10_000, "não respeitou o tempo limite");
  } finally {
    lento.parar();
  }
});

for (const invalido of ["57-abc", "571", "57-", "-1", "57-1234567890", "1234567890-1", "abc-123"]) {
  test(`id malformado dá 404 sem chamar a API: ${invalido}`, async () => {
    const controle = await pagina();
    assert.equal(controle.status, 200, "controle: a página precisa existir");
    const antes = api.chamadas.length;

    const { status } = await pagina(invalido);

    assert.equal(status, 404);
    assert.equal(api.chamadas.length, antes, "chamou a API com um id inválido");
  });
}

test("id válido: a API recebe exatamente GET /internal/v1/deputados/<id>/", async () => {
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
