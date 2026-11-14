// Página do senador (`/senado/senadores/<codigo>/`, ADR 0028), contra o servidor de produção e uma
// API falsa. Dados todos sintéticos. O que mais importa: quem saiu da lista de exercício aparece
// como "fora da lista" com a ressalva de que a data é a da COLETA (a fonte não diz o motivo), só
// sai o que a página conhece, link da fonte só se for http(s) e a falha da API não vaza.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

const CODIGO = "5012";
const CAMINHO_DA_API = `GET /internal/v1/senadores/${CODIGO}/`;

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
    fonte: "Senado Federal: Dados Abertos",
    conjunto: "Senadores em exercício",
    coletado_em: "2026-11-13T09:00:00+00:00",
    url_origem: "https://dados.example.org/dadosabertos/senador/lista/atual.json",
    licenca: { id: null, url: null },
    ...extra,
  };
}

function perfil({ senador = {}, atribuicao, ...extra } = {}) {
  return {
    senador: {
      id_senado: 5012,
      nome: "Ana do Senado",
      partido: "XYZ",
      uf: "SP",
      em_exercicio: true,
      saiu_da_lista_em: null,
      ...senador,
    },
    atribuicao: atribuicao ?? atribuicaoPadrao(),
    ...extra,
  };
}

async function pagina(codigo = CODIGO, resposta = { status: 200, corpo: perfil() }) {
  api.resposta = () => resposta;
  const retorno = await fetch(`${front.base}/senado/senadores/${codigo}/`);
  return { status: retorno.status, html: await retorno.text() };
}

test("senador: nome, partido, UF e código no Senado", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200);
  assert.match(html, /<h1[^>]*>Ana do Senado<\/h1>/);
  for (const trecho of ["XYZ", "SP", "5012"]) {
    assert.ok(html.includes(trecho), `faltou "${trecho}" no HTML`);
  }
});

test("em exercício: a página diz isso e não fala de saída", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(html.includes("Em exercício"));
  assert.ok(!html.includes("Fora da lista"));
});

test("fora da lista: mostra a data da coleta e a ressalva de que não é o fim do mandato", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  const { html } = await pagina(CODIGO, {
    status: 200,
    corpo: perfil({
      senador: { em_exercicio: false, saiu_da_lista_em: "2026-11-12T20:00:00+00:00" },
    }),
  });

  assert.ok(html.includes("Fora da lista"));
  // 2026-11-12T20:00Z é 12/11/2026 17:00 em Brasília.
  assert.match(html, /12\/11\/2026[^<]*17:00/);
  assert.match(html, /coleta/i);
  assert.match(html, /não diz o motivo/i);
  assert.ok(!html.includes("Em exercício"));
});

test("partido nulo some da página; 'S/Partido' vira 'Sem partido'", async () => {
  const controle = await pagina();
  assert.ok(controle.html.includes("Partido"), "controle: com partido o rótulo aparece");

  const nulo = await pagina(CODIGO, { status: 200, corpo: perfil({ senador: { partido: null } }) });
  assert.equal(nulo.status, 200);
  assert.ok(!nulo.html.includes("Partido"));
  assert.ok(!nulo.html.includes(">null<"));

  const sem = await pagina(CODIGO, {
    status: 200,
    corpo: perfil({ senador: { partido: "S/Partido" } }),
  });
  assert.ok(sem.html.includes("Sem partido"));
  assert.ok(!sem.html.includes("S/Partido"));
});

test("atribuição: fonte, conjunto, coleta em horário de Brasília e link do original", async () => {
  const { html } = await pagina();

  assert.ok(html.includes("Senado Federal: Dados Abertos"));
  assert.ok(html.includes("Senadores em exercício"));
  // 2026-11-13T09:00Z é 13/11/2026 06:00 em Brasília.
  assert.match(html, /13\/11\/2026[^<]*06:00/);
  assert.ok(
    html.includes('href="https://dados.example.org/dadosabertos/senador/lista/atual.json"'),
  );
});

for (const perigoso of ["javascript:alert(1)", "data:text/html,<b>x</b>", "//evil.example.org/x"]) {
  test(`link da fonte que não é http(s) vira texto, sem href: ${perigoso}`, async () => {
    const atribuicao = atribuicaoPadrao({ url_origem: perigoso });
    const { status, html } = await pagina(CODIGO, { status: 200, corpo: perfil({ atribuicao }) });

    assert.equal(status, 200, "controle: a página precisa existir");
    assert.ok(!/href="(javascript|data|vbscript|ftp|\/\/)/i.test(html), "virou href");
  });
}

test("nome com HTML aparece escapado, sem tag ativa", async () => {
  const { status, html } = await pagina(CODIGO, {
    status: 200,
    corpo: perfil({ senador: { nome: "<script>alert(1)</script>" } }),
  });

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("<script>alert(1)</script>"));
  assert.ok(html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));
});

test("chave desconhecida que a API devolva não chega ao HTML", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  const corpo = perfil({ campo_extra: "SEGREDO-NA-RAIZ" });
  corpo.senador.email = "SEGREDO-NO-SENADOR";
  corpo.atribuicao.interno = "SEGREDO-NA-ATRIBUICAO";
  const { html } = await pagina(CODIGO, { status: 200, corpo });

  assert.ok(!html.includes("SEGREDO"));
});

test("API responde 404: página 404 em português", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: sem a rota, o 404 viria do Next e não da API");
  api.chamadas.length = 0;

  const { status, html } = await pagina(CODIGO, { status: 404, corpo: { erro: "não encontrado" } });

  assert.equal(status, 404);
  assert.match(html, /não encontrad/i);
  assert.deepEqual(api.chamadas, [CAMINHO_DA_API], "a API não foi chamada");
});

test("API responde 500: erro genérico, sem o endereço da API", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  const { status, html } = await pagina(CODIGO, { status: 500, corpo: { erro: "boom" } });

  assert.equal(status, 500);
  assert.ok(!html.includes(api.url));
  assert.ok(!html.includes(new URL(api.url).host));
});

test("resposta fora do formato esperado: erro 500 genérico, sem o texto da resposta", async () => {
  const { status, html } = await pagina(CODIGO, {
    status: 200,
    corpo: { senador: { nome: 42 }, atribuicao: "SEGREDO-FORA-DO-FORMATO" },
  });

  assert.equal(status, 500);
  assert.ok(!html.includes("SEGREDO"));
});

test("`em_exercicio` que não é booleano é recusado", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: com booleano a página existe");

  const { status } = await pagina(CODIGO, {
    status: 200,
    corpo: perfil({ senador: { em_exercicio: "true" } }),
  });

  assert.equal(status, 500);
});

for (const invalido of ["abc", "1234567890", "-1", "5012x", "50.12"]) {
  test(`código malformado dá 404 sem chamar a API: ${invalido}`, async () => {
    const controle = await pagina();
    assert.equal(controle.status, 200, "controle: o código válido precisa dar 200");
    api.chamadas.length = 0;

    const { status } = await pagina(encodeURIComponent(invalido));

    assert.equal(status, 404);
    assert.deepEqual(api.chamadas, [], "o front chamou a API com código inválido");
  });
}

test("estrutura: um h1, título com o descritor e noindex", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200, "controle: a 404 do Next também tem h1, título e noindex");
  assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1);
  assert.match(html, /<title>[^<]*transparência e inteligência cívica[^<]*<\/title>/);
  assert.match(html, /<meta name="robots" content="noindex/);
});
