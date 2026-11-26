// Votos do deputado na página `/deputados/<legislatura>-<id>/`, contra o servidor de produção e uma
// API falsa. Dados todos sintéticos. O que mais importa: a página pede à API a rota e a página
// certas, `voto` nulo aparece como "sem posição registrada" (e não como vazio ou "null"), o partido
// é o da época do voto (não o do perfil), resposta fora do formato derruba a página sem vazar o
// texto dela, e o 404 do perfil continua sendo 404 sem chamar a rota de votos.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

const ID = "57-204554";
const CAMINHO_DO_PERFIL = `GET /internal/v1/deputados/${ID}/`;
const CAMINHO_DOS_VOTOS = `GET /internal/v1/deputados/${ID}/votos/`;

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

// O partido do perfil é "XYZ"; os dos votos, "ABC" e "DEF": nenhum teste pode passar por acaso
// porque o partido do voto coincide com o do perfil.
function perfil() {
  return {
    deputado: { legislatura: 57, id_camara: 204554, nome: "ANA DA CÂMARA", partido: "XYZ", uf: "SP" },
    atribuicao: atribuicaoPadrao(),
  };
}

function atribuicaoDosVotos(extra = {}) {
  return atribuicaoPadrao({
    conjunto: "Votos nominais em plenário",
    url_origem: "https://dados.example.org/api/v2/votacoes/votos.json",
    ...extra,
  });
}

// Data, órgão, descrição e aprovação de cada item vêm do conjunto das votações, outro arquivo que o
// dos votos: a página cita os dois.
function atribuicaoDasVotacoes(extra = {}) {
  return atribuicaoPadrao({
    conjunto: "Votações em plenário",
    coletado_em: "2026-11-10T12:00:00+00:00",
    url_origem: "https://dados.example.org/api/v2/votacoes/votacoes.json",
    ...extra,
  });
}

function itemDeVoto(extra = {}) {
  return {
    id: "2641546-7",
    data: "2026-11-12",
    orgao: "Plenário",
    descricao: "Aprovada a Medida Provisória nº 1/2026.",
    // A API só emite "1", "0" ou null aqui; o significado não foi verificado (ADR 0031 e 0032).
    aprovacao: "1",
    id_proposicao: 9876543,
    partido: "ABC",
    voto: "Sim",
    ...extra,
  };
}

// Como a API: as duas atribuições existem juntas, e só quando a página tem votos.
function historico({
  votos = [itemDeVoto()],
  pagina = 1,
  total_paginas = 1,
  atribuicao_dos_votos,
  atribuicao_das_votacoes,
} = {}) {
  const temVotos = votos.length > 0;
  return {
    deputado: { legislatura: 57, id_camara: 204554, nome: "ANA DA CÂMARA" },
    votos,
    pagina,
    total_paginas,
    atribuicao_das_votacoes:
      atribuicao_das_votacoes === undefined
        ? temVotos
          ? atribuicaoDasVotacoes()
          : null
        : atribuicao_das_votacoes,
    atribuicao_dos_votos:
      atribuicao_dos_votos === undefined
        ? temVotos
          ? atribuicaoDosVotos()
          : null
        : atribuicao_dos_votos,
  };
}

// A página chama duas rotas da API: o perfil e os votos. `resposta` vale para o perfil e `votos`
// para a lista; `consulta` é a query string da página do front (ex.: "?pagina=2").
async function pagina(
  id = ID,
  resposta = { status: 200, corpo: perfil() },
  { votos = { status: 200, corpo: historico() }, consulta = "" } = {},
) {
  api.resposta = (req) => (req.url.startsWith(`/internal/v1/deputados/${id}/votos/`) ? votos : resposta);
  const retorno = await fetch(`${front.base}/deputados/${id}/${consulta}`);
  return { status: retorno.status, html: await retorno.text() };
}

const comVotos = (corpo, consulta = "") =>
  pagina(ID, { status: 200, corpo: perfil() }, { votos: { status: 200, corpo }, consulta });

// A linha da tabela que contém o texto dado, só até o `</tr>` (depois dela o HTML ainda tem o
// resto da página e o payload do Next, que repetiria o texto das outras linhas).
function linhaCom(html, texto) {
  return html.split("</tr>").find((trecho) => trecho.includes(texto));
}

// O texto de cada `<td>` da linha que contém `texto`, na ordem das colunas.
function celulas(html, texto) {
  const linha = linhaCom(html, texto);
  assert.ok(linha, `não achei a linha com "${texto}"`);
  return Array.from(linha.matchAll(/<td[^>]*>(.*?)<\/td>/gs), (achado) => achado[1]);
}

test("votos: cada dado cai na sua coluna (data, órgão, descrição, aprovação, partido, voto)", async () => {
  const { status, html } = await comVotos(
    historico({
      votos: [
        itemDeVoto({ id: "1-1", descricao: "Descrição A" }),
        itemDeVoto({
          id: "2-1",
          data: "2026-03-05",
          orgao: "Comissão de Teste",
          descricao: "Descrição B",
          aprovacao: "0",
          partido: "DEF",
          voto: "Não",
        }),
      ],
    }),
  );

  assert.equal(status, 200);
  assert.deepEqual(celulas(html, "Descrição A"), [
    "12/11/2026",
    "Plenário",
    "Descrição A",
    "1",
    "ABC",
    "Sim",
  ]);
  assert.deepEqual(celulas(html, "Descrição B"), [
    "05/03/2026",
    "Comissão de Teste",
    "Descrição B",
    "0",
    "DEF",
    "Não",
  ]);
  const cabecalho = Array.from(html.matchAll(/<th\s[^>]*>(.*?)<\/th>/g), (achado) => achado[1]);
  assert.deepEqual(cabecalho, [
    "Data",
    "Órgão",
    "Descrição",
    "Aprovação (código da fonte)",
    "Partido (à época)",
    "Voto",
  ]);
});

test("votos: o código da fonte não é traduzido e a nota diz que o significado não foi verificado", async () => {
  const { status, html } = await comVotos(historico());

  assert.equal(status, 200);
  assert.ok(!/<th\s[^>]*>Resultado/.test(html), "a coluna ainda se chama Resultado");
  assert.match(
    html,
    /Códigos como a fonte os manda; o significado de 1\/0 e das siglas de voto não foi verificado\./,
  );
});

test("votos: partidos diferentes na mesma página saem cada um na sua linha, não o do perfil", async () => {
  const { status, html } = await comVotos(
    historico({
      votos: [
        itemDeVoto({ id: "1-1", descricao: "Descrição A", partido: "ABC", voto: "Sim" }),
        itemDeVoto({ id: "2-1", descricao: "Descrição B", partido: "DEF", voto: "Não" }),
      ],
    }),
  );

  assert.equal(status, 200);
  const a = linhaCom(html, "Descrição A");
  const b = linhaCom(html, "Descrição B");
  assert.ok(a?.includes("ABC") && a.includes("Sim") && !a.includes("DEF"), "linha A");
  assert.ok(b?.includes("DEF") && b.includes("Não") && !b.includes("ABC"), "linha B");
  assert.ok(!a.includes("XYZ") && !b.includes("XYZ"), "o partido do perfil entrou na linha do voto");
});

test("votos: `voto` nulo aparece como 'sem posição registrada', nunca vazio nem 'null'", async () => {
  const controle = await comVotos(historico());
  assert.ok(!/sem posição registrada/i.test(controle.html), "controle: com voto a frase não aparece");

  const { status, html } = await comVotos(
    historico({
      votos: [
        itemDeVoto({ id: "1-1", descricao: "Descrição A", voto: "Sim" }),
        itemDeVoto({ id: "2-1", descricao: "Descrição B", voto: null }),
      ],
    }),
  );

  assert.equal(status, 200);
  assert.match(linhaCom(html, "Descrição B"), /sem posição registrada/i);
  assert.ok(!/sem posição registrada/i.test(linhaCom(html, "Descrição A")));
  assert.equal(celulas(html, "Descrição A")[5], "Sim");
  assert.equal(celulas(html, "Descrição B")[5], "Sem posição registrada");
});

test("votos: `aprovacao` nula deixa a célula vazia; a outra linha mantém o código", async () => {
  const { status, html } = await comVotos(
    historico({
      votos: [
        itemDeVoto({ id: "1-1", descricao: "Descrição A", aprovacao: "0" }),
        itemDeVoto({ id: "2-1", descricao: "Descrição B", aprovacao: null }),
      ],
    }),
  );

  assert.equal(status, 200);
  assert.equal(celulas(html, "Descrição A")[3], "0");
  assert.equal(celulas(html, "Descrição B")[3], "");
  assert.ok(!html.includes(">null<"));
});

test("votos: `partido` nulo não vira 'null' na tela", async () => {
  const { status, html } = await comVotos(historico({ votos: [itemDeVoto({ partido: null })] }));

  assert.equal(status, 200);
  const [, , descricao, , partido] = celulas(html, "Aprovada a Medida Provisória nº 1/2026.");
  assert.equal(descricao, "Aprovada a Medida Provisória nº 1/2026.");
  assert.equal(partido, "", "o partido nulo tem de deixar a célula vazia");
});

test("votos: sem link para proposição e sem mostrar o id da proposição", async () => {
  const { status, html } = await comVotos(historico());

  assert.equal(status, 200);
  assert.ok(html.includes("Aprovada a Medida Provisória nº 1/2026."), "controle: o voto aparece");
  assert.ok(!html.includes("9876543"), "mostrou id_proposicao");
  // Na página inteira, menos o link do menu (`/camara/votacoes/`, que o layout tem desde a página
  // das votações da Câmara e que não é um link por proposição): qualquer outro `/camara` é recusado.
  assert.ok(html.includes('href="/camara/votacoes/"'), "controle: o menu tem o link das votações");
  assert.ok(!/href="\/camara(?!\/votacoes\/")/.test(html), "criou link para /camara");
});

test("votos: a API recebe o perfil e depois GET .../votos/?pagina=1", async () => {
  api.chamadas.length = 0;

  const { status } = await pagina();

  assert.equal(status, 200);
  assert.deepEqual(api.chamadas, [CAMINHO_DO_PERFIL, `${CAMINHO_DOS_VOTOS}?pagina=1`]);
});

test("votos: primeira de duas páginas tem 'Próxima' e não tem 'Anterior'", async () => {
  const { html } = await comVotos(historico({ pagina: 1, total_paginas: 2 }));

  assert.ok(html.includes(`href="/deputados/${ID}/?pagina=2"`));
  assert.ok(html.includes("Próxima"));
  assert.ok(!html.includes("Anterior"));
});

test("votos: última página tem 'Anterior' e não tem 'Próxima'", async () => {
  const { html } = await comVotos(historico({ pagina: 2, total_paginas: 2 }), "?pagina=2");

  assert.ok(html.includes(`href="/deputados/${ID}/?pagina=1"`));
  assert.ok(html.includes("Anterior"));
  assert.ok(!html.includes("Próxima"));
});

test("votos: página do meio de três tem as duas setas, com as páginas 2 e 4", async () => {
  const { html } = await comVotos(historico({ pagina: 3, total_paginas: 5 }), "?pagina=3");

  assert.ok(html.includes(`href="/deputados/${ID}/?pagina=2"`));
  assert.ok(html.includes(`href="/deputados/${ID}/?pagina=4"`));
  assert.ok(html.includes("Página 3 de 5"));
});

test("votos: a página pedida vai à API; página inválida vira 1", async () => {
  api.chamadas.length = 0;
  await comVotos(historico({ pagina: 2, total_paginas: 2 }), "?pagina=2");
  assert.deepEqual(api.chamadas, [CAMINHO_DO_PERFIL, `${CAMINHO_DOS_VOTOS}?pagina=2`]);

  // A regra do `?pagina=` é `[1-9][0-9]{0,3}` (sem zero à esquerda, ASCII).
  for (const invalida of ["0", "abc", "-1", "12345", "02", "0002", "٢"]) {
    api.chamadas.length = 0;
    const { status } = await comVotos(historico(), `?pagina=${invalida}`);

    assert.equal(status, 200, `a página não pode quebrar com ?pagina=${invalida}`);
    assert.deepEqual(
      api.chamadas,
      [CAMINHO_DO_PERFIL, `${CAMINHO_DOS_VOTOS}?pagina=1`],
      `?pagina=${invalida}`,
    );
  }
});

test("votos: sem nenhum voto coletado a página diz isso e o perfil continua", async () => {
  const { status, html } = await comVotos(
    historico({ votos: [], pagina: 1, total_paginas: 0 }),
  );

  assert.equal(status, 200);
  assert.ok(html.includes("Nenhum voto coletado"));
  assert.ok(!html.includes("Votos nominais em plenário"), "sem votos não há o que citar");
  assert.ok(!html.includes("Votações em plenário"), "sem votos não há o que citar");
  assert.ok(html.includes("ANA DA CÂMARA"));
  assert.ok(!html.includes("não foi verificado"), "a nota dos códigos sem tabela não faz sentido");
});

test("votos: página além da última volta para a primeira", async () => {
  const { status, html } = await comVotos(
    historico({ votos: [], pagina: 9, total_paginas: 2 }),
    "?pagina=9",
  );

  assert.equal(status, 200);
  assert.ok(html.includes("Nenhum voto nesta página"));
  assert.ok(html.includes(`href="/deputados/${ID}/"`));
  assert.ok(!html.includes("Anterior"), "não há setas na página vazia");
  assert.ok(!html.includes("Próxima"), "não há setas na página vazia");
  assert.ok(!html.includes("não foi verificado"), "a nota dos códigos sem tabela não faz sentido");
});

test("votos: a atribuição dos votos aparece com o conjunto e o link do original", async () => {
  const { html } = await comVotos(historico());

  assert.ok(html.includes("Votos nominais em plenário"));
  assert.ok(html.includes('href="https://dados.example.org/api/v2/votacoes/votos.json"'));
});

test("votos: a atribuição das votações aparece à parte, com o conjunto e o link do original", async () => {
  const { html } = await comVotos(historico());

  assert.ok(html.includes("Votações em plenário"));
  assert.ok(html.includes('href="https://dados.example.org/api/v2/votacoes/votacoes.json"'));
});

test("votos: as três origens da página (perfil, votações e votos) aparecem, cada uma uma vez", async () => {
  const { html } = await comVotos(historico());

  for (const conjunto of [
    "Deputados em exercício (legislatura atual)",
    "Votações em plenário",
    "Votos nominais em plenário",
  ]) {
    assert.equal(html.split(`<dd>${conjunto}</dd>`).length - 1, 1, conjunto);
  }
  assert.equal((html.match(/<h3>Origem dos dados<\/h3>/g) ?? []).length, 3);
});

test("votos: a atribuição das votações fica dentro da seção de votos", async () => {
  const { html } = await comVotos(historico());

  // A seção de votos é a última da página: tudo o que vem depois do seu `aria-labelledby` é dela.
  const inicio = html.indexOf('aria-labelledby="deputado-votos"');
  assert.ok(inicio > 0, "não achei a seção de votos");
  const antes = html.slice(0, inicio);
  const depois = html.slice(inicio);
  assert.ok(antes.includes("<dd>Deputados em exercício (legislatura atual)</dd>"));
  assert.ok(!antes.includes("<dd>Votações em plenário</dd>"));
  assert.ok(depois.includes("<dd>Votações em plenário</dd>"));
  assert.ok(depois.includes("<dd>Votos nominais em plenário</dd>"));
  assert.ok(!depois.includes("<dd>Deputados em exercício"), "a origem do perfil fica na outra seção");
});

// Guarda de regressão, passa antes e depois da implementação (o `Atribuicao` já recusava o link).
test("votos: link da atribuição que não é http(s) vira texto, sem href", async () => {
  const perigosa = { url_origem: "javascript:alert(1)" };
  const { status, html } = await comVotos(
    historico({
      atribuicao_dos_votos: atribuicaoDosVotos(perigosa),
      atribuicao_das_votacoes: atribuicaoDasVotacoes(perigosa),
    }),
  );

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!/href="javascript/i.test(html), "virou href");
});

test("votos: órgão, descrição, aprovação, partido e voto com HTML aparecem escapados", async () => {
  const { status, html } = await comVotos(
    historico({
      votos: [
        itemDeVoto({
          orgao: "<img src=x>",
          descricao: "<script>alert(1)</script>",
          aprovacao: "<s>1</s>",
          partido: "<u>ABC</u>",
          voto: "<b>Sim</b>",
        }),
      ],
    }),
  );

  assert.equal(status, 200);
  for (const cru of [
    "<script>alert(1)",
    "<img src=x>",
    "<s>1</s>",
    "<u>ABC</u>",
    "<b>Sim</b>",
  ]) {
    assert.ok(!html.includes(cru), `${cru} saiu sem escapar`);
  }
  for (const escapado of [
    "&lt;script&gt;alert(1)&lt;/script&gt;",
    "&lt;s&gt;1&lt;/s&gt;",
    "&lt;u&gt;ABC&lt;/u&gt;",
    "&lt;b&gt;Sim&lt;/b&gt;",
  ]) {
    assert.ok(html.includes(escapado), `faltou ${escapado}`);
  }
});

// Guarda de regressão, passa antes e depois da implementação (a página só mostra o que conhece).
test("votos: chave desconhecida que a API devolva não chega ao HTML", async () => {
  const corpo = historico({ votos: [itemDeVoto({ interno: "SEGREDO-NO-ITEM" })] });
  corpo.extra = "SEGREDO-NA-RAIZ";
  corpo.deputado.email = "SEGREDO-NO-DEPUTADO";
  corpo.atribuicao_dos_votos.interno = "SEGREDO-NA-ATRIBUICAO-DOS-VOTOS";
  corpo.atribuicao_das_votacoes.interno = "SEGREDO-NA-ATRIBUICAO-DAS-VOTACOES";

  const { status, html } = await comVotos(corpo);

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("SEGREDO"));
});

test("votos: estrutura: um h1 e a seção 'Votos'", async () => {
  const { status, html } = await comVotos(historico());

  assert.equal(status, 200);
  assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1);
  assert.match(html, /<h2[^>]*>Votos<\/h2>/);
});

// Cada caso quebra uma única chave do formato; o controle (histórico íntegro) precisa dar 200.
const CORPOS_FORA_DO_FORMATO = {
  "voto de tipo errado": (c) => (c.votos[0].voto = 7),
  "voto ausente": (c) => delete c.votos[0].voto,
  "partido de tipo errado": (c) => (c.votos[0].partido = 7),
  "partido ausente": (c) => delete c.votos[0].partido,
  "aprovacao de tipo errado": (c) => (c.votos[0].aprovacao = 1),
  "id do voto numérico": (c) => (c.votos[0].id = 2641546),
  "data numérica": (c) => (c.votos[0].data = 20261112),
  "orgao nulo": (c) => (c.votos[0].orgao = null),
  "descricao nula": (c) => (c.votos[0].descricao = null),
  "id_proposicao em texto": (c) => (c.votos[0].id_proposicao = "9876543"),
  "item que não é objeto": (c) => (c.votos[0] = "SEGREDO-FORA-DO-FORMATO"),
  "votos que não é lista": (c) => (c.votos = "SEGREDO-FORA-DO-FORMATO"),
  "pagina em texto": (c) => (c.pagina = "1"),
  "total_paginas ausente": (c) => delete c.total_paginas,
  "atribuicao_dos_votos que não é objeto": (c) =>
    (c.atribuicao_dos_votos = "SEGREDO-FORA-DO-FORMATO"),
  "atribuicao_dos_votos sem conjunto": (c) => delete c.atribuicao_dos_votos.conjunto,
  "atribuicao_dos_votos ausente": (c) => delete c.atribuicao_dos_votos,
  "atribuicao_dos_votos nula com votos": (c) => (c.atribuicao_dos_votos = null),
  "atribuicao_das_votacoes que não é objeto": (c) =>
    (c.atribuicao_das_votacoes = "SEGREDO-FORA-DO-FORMATO"),
  "atribuicao_das_votacoes sem conjunto": (c) => delete c.atribuicao_das_votacoes.conjunto,
  "atribuicao_das_votacoes ausente": (c) => delete c.atribuicao_das_votacoes,
  "atribuicao_das_votacoes nula com votos": (c) => (c.atribuicao_das_votacoes = null),
  "só a chave antiga 'atribuicao'": (c) => {
    c.atribuicao = c.atribuicao_dos_votos;
    delete c.atribuicao_dos_votos;
    delete c.atribuicao_das_votacoes;
  },
  "atribuicao_dos_votos com a lista vazia": (c) => {
    c.votos = [];
    c.atribuicao_das_votacoes = null;
  },
  "atribuicao_das_votacoes com a lista vazia": (c) => {
    c.votos = [];
    c.atribuicao_dos_votos = null;
  },
  "deputado sem nome": (c) => delete c.deputado.nome,
  "deputado.legislatura em texto": (c) => (c.deputado.legislatura = "57"),
  "deputado.id_camara em texto": (c) => (c.deputado.id_camara = "204554"),
};

for (const [nome, estragar] of Object.entries(CORPOS_FORA_DO_FORMATO)) {
  test(`votos: resposta fora do formato (${nome}) vira 500 sem vazar o texto`, async () => {
    const controle = await comVotos(historico());
    assert.equal(controle.status, 200, "controle: o histórico íntegro precisa dar 200");

    const corpo = historico();
    estragar(corpo);
    const { status, html } = await comVotos(corpo);

    assert.equal(status, 500);
    assert.ok(!html.includes("SEGREDO"));
  });
}

test("votos: corpo que não é JSON vira 500 sem vazar o texto", async () => {
  const { status, html } = await comVotos("SEGREDO-NAO-E-JSON");

  assert.equal(status, 500);
  assert.ok(!html.includes("SEGREDO"));
});

test("votos: API de votos com erro dá 500 genérico, sem o endereço da API", async () => {
  const controle = await comVotos(historico());
  assert.equal(controle.status, 200, "controle: com os votos a página precisa existir");

  const { status, html } = await pagina(
    ID,
    { status: 200, corpo: perfil() },
    { votos: { status: 500, corpo: { erro: "boom" } } },
  );

  assert.equal(status, 500);
  assert.ok(!html.includes(api.url));
  assert.ok(!html.includes(new URL(api.url).host));
});

test("votos: 404 dos votos com o perfil existente é incoerência da API e vira 500", async () => {
  const controle = await comVotos(historico());
  assert.equal(controle.status, 200, "controle: a página precisa existir");

  const { status } = await pagina(
    ID,
    { status: 200, corpo: perfil() },
    { votos: { status: 404, corpo: { erro: "não encontrado" } } },
  );

  assert.equal(status, 500);
});

// Guarda de regressão, passa antes e depois da implementação (sem ela a página nem chama os votos).
test("votos: perfil 404 continua 404 e não chama a API de votos", async () => {
  const controle = await comVotos(historico());
  assert.equal(controle.status, 200, "controle: a página precisa existir");
  api.chamadas.length = 0;

  const { status, html } = await pagina(ID, { status: 404, corpo: { erro: "não encontrado" } });

  assert.equal(status, 404);
  assert.match(html, /não encontrad/i);
  assert.deepEqual(api.chamadas, [CAMINHO_DO_PERFIL]);
});
