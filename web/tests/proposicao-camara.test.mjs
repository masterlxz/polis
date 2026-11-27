// Tramitação de uma proposição da Câmara (`/camara/proposicoes/<id>/`, ADR 0035), contra o servidor
// de produção e uma API falsa. Dados todos sintéticos. O que mais importa: a hora aparece em
// Brasília a partir do instante que a API manda (e não cortando o texto); título, ementa, órgão e
// descrição são texto livre da fonte e saem escapados; `sequencia` não é mostrada (o significado
// dela não foi verificado); a nota diz que são só as tramitações de 2026 e que o fuso não foi
// verificado; id inválido é 404 sem chamar a API; e uma resposta fora do formato derruba a página
// sem vazar o texto dela.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

const NOTA =
  "Tramitações de 2026. A hora é a da fonte, gravada como horário de Brasília (não verificado).";
const SEM_TRAMITACAO = "Sem tramitação de 2026 para esta proposição.";

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

function atribuicaoDaProposicao(extra = {}) {
  return {
    fonte: "Câmara dos Deputados: Dados Abertos",
    conjunto: "Proposições das votações da Câmara (2026)",
    coletado_em: "2026-11-26T08:00:00+00:00",
    url_origem: "https://dados.example.org/arquivos/votacoesProposicoes/csv/votacoesProposicoes.csv",
    licenca: { id: null, url: null },
    ...extra,
  };
}

function atribuicaoDasTramitacoes(extra = {}) {
  return {
    fonte: "Câmara dos Deputados: Dados Abertos",
    conjunto: "Tramitações das proposições da Câmara (2026)",
    coletado_em: "2026-11-27T12:53:00+00:00",
    url_origem: "https://dados.example.org/arquivos/proposicoesTramitacoes/csv/tramitacoes-2026.csv",
    licenca: { id: null, url: null },
    ...extra,
  };
}

// `sequencia` é um número que não aparece em nenhuma outra parte da fixture: a página não o mostra.
function tramitacao(extra = {}) {
  return {
    sequencia: 87654321,
    data_hora: "2026-05-07T16:58:00-03:00",
    orgao: "MESA",
    descricao: "Apresentação de Requerimento",
    ...extra,
  };
}

function resposta(extra = {}) {
  return {
    proposicao: {
      id_camara: 4455667,
      titulo: "PL 11/2003",
      tipo: "PL",
      numero: 11,
      ano: 2003,
      ementa: "Proíbe a veiculação de peças publicitárias.",
    },
    tramitacoes: [tramitacao()],
    atribuicao_da_proposicao: atribuicaoDaProposicao(),
    atribuicao_das_tramitacoes: atribuicaoDasTramitacoes(),
    ...extra,
  };
}

async function abrir(caminho, corpoDaApi) {
  api.resposta = () => corpoDaApi;
  const retorno = await fetch(`${front.base}${caminho}`);
  return { status: retorno.status, html: await retorno.text() };
}

const pagina = (corpo = resposta(), id = corpo?.proposicao?.id_camara ?? 4455667) =>
  abrir(`/camara/proposicoes/${id}/`, { status: 200, corpo });

// A tabela cuja legenda (`<caption>`) é `legenda`: cabeçalho e linhas, cada célula em texto.
function tabela(html, legenda) {
  const corpo = Array.from(html.matchAll(/<table[^>]*>(.*?)<\/table>/gs), (achado) => achado[1]).find(
    (conteudo) => conteudo.includes(`<caption>${legenda}</caption>`),
  );
  if (corpo === undefined) return null;
  const celulas = (linha, marca) =>
    Array.from(linha.matchAll(new RegExp(`<${marca}[^>]*>(.*?)</${marca}>`, "gs")), (a) => a[1]);
  const linhas = Array.from(corpo.matchAll(/<tr[^>]*>(.*?)<\/tr>/gs), (achado) => achado[1]);
  return {
    cabecalho: linhas.flatMap((linha) => celulas(linha, "th")),
    linhas: linhas.map((linha) => celulas(linha, "td")).filter((c) => c.length > 0),
  };
}

// --- A página ----------------------------------------------------------------------------------

test("proposição: título no h1, tipo, número e ano, e a ementa", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200);
  assert.match(html, /<h1[^>]*>PL 11\/2003<\/h1>/);
  assert.match(html, /<p class="ementa">Proíbe a veiculação de peças publicitárias\.<\/p>/);
});

test("proposição: chama a API uma vez, na rota da proposição", async () => {
  api.chamadas.length = 0;

  const { status } = await pagina();

  assert.equal(status, 200, "controle: a página existe");
  assert.deepEqual(api.chamadas, ["GET /internal/v1/camara/proposicoes/4455667/"]);
});

test("proposição: tabela de tramitações com Data e hora, Órgão e Descrição, cada dado na sua coluna", async () => {
  const { html } = await pagina();

  const tramitacoes = tabela(html, "Tramitações");
  assert.ok(tramitacoes, "não achei a tabela de tramitações");
  assert.deepEqual(tramitacoes.cabecalho, ["Data e hora", "Órgão", "Descrição"]);
  assert.deepEqual(tramitacoes.linhas, [
    ["07/05/2026 às 16:58", "MESA", "Apresentação de Requerimento"],
  ]);
});

test("proposição: as linhas saem na ordem que a API manda", async () => {
  const { html } = await pagina(
    resposta({
      tramitacoes: [
        tramitacao({ orgao: "PLEN", descricao: "Primeira" }),
        tramitacao({ orgao: "CCJC", descricao: "Segunda" }),
        tramitacao({ orgao: "MESA", descricao: "Terceira" }),
      ],
    }),
  );

  assert.deepEqual(
    tabela(html, "Tramitações").linhas.map((linha) => linha[2]),
    ["Primeira", "Segunda", "Terceira"],
  );
});

test("proposição: a hora é convertida para Brasília a partir do instante, não cortada do texto", async () => {
  const { html } = await pagina(
    resposta({
      tramitacoes: [
        tramitacao({ data_hora: "2026-05-07T19:58:00+00:00", descricao: "Em UTC" }),
        tramitacao({ data_hora: "2026-01-02T00:00:00-03:00", descricao: "Meia-noite" }),
      ],
    }),
  );

  assert.deepEqual(
    tabela(html, "Tramitações").linhas.map((linha) => [linha[0], linha[2]]),
    [
      ["07/05/2026 às 16:58", "Em UTC"],
      ["02/01/2026 às 00:00", "Meia-noite"],
    ],
  );
});

test("proposição: a sequência não aparece", async () => {
  const { status, html } = await pagina();

  assert.equal(status, 200, "controle: a página existe");
  assert.ok(!html.includes("87654321"));
});

test("proposição: a nota diz que são só as tramitações de 2026 e que o fuso não foi verificado", async () => {
  const { html } = await pagina();

  assert.ok(html.includes(NOTA));
});

test("proposição sem tramitação: aviso, nenhuma tabela e só a atribuição da proposição", async () => {
  const { status, html } = await pagina(
    resposta({ tramitacoes: [], atribuicao_das_tramitacoes: null }),
  );

  assert.equal(status, 200);
  assert.ok(html.includes(SEM_TRAMITACAO));
  assert.equal(tabela(html, "Tramitações"), null);
  assert.ok(html.includes("Proposições das votações da Câmara (2026)"));
  assert.ok(!html.includes("Tramitações das proposições da Câmara (2026)"));
});

test("proposição com tramitação: as duas atribuições, cada uma com o conjunto e o endereço de origem", async () => {
  const { html } = await pagina();

  for (const texto of [
    "Proposições das votações da Câmara (2026)",
    "https://dados.example.org/arquivos/votacoesProposicoes/csv/votacoesProposicoes.csv",
    "Tramitações das proposições da Câmara (2026)",
    "https://dados.example.org/arquivos/proposicoesTramitacoes/csv/tramitacoes-2026.csv",
  ]) {
    assert.ok(html.includes(texto), `faltou: ${texto}`);
  }
  assert.equal((html.match(/<h3>Origem dos dados<\/h3>/g) ?? []).length, 2);
});

test("proposição: ano e ementa nulos não viram 'null' nem texto vazio", async () => {
  const corpo = resposta();
  corpo.proposicao.ano = null;
  corpo.proposicao.ementa = null;

  const { status, html } = await pagina(corpo);

  assert.equal(status, 200);
  assert.ok(!html.includes("null"));
  assert.ok(!/<p class="ementa">\s*<\/p>/.test(html));
});

test("proposição: título, ementa, órgão e descrição com HTML aparecem escapados", async () => {
  const corpo = resposta({
    tramitacoes: [tramitacao({ orgao: "<i>o</i>", descricao: "<script>d</script>" })],
  });
  corpo.proposicao.titulo = "<b>t</b>";
  corpo.proposicao.ementa = "<u>e</u>";

  const { html } = await pagina(corpo);

  assert.ok(html.includes("&lt;b&gt;t&lt;/b&gt;"));
  assert.ok(html.includes("&lt;u&gt;e&lt;/u&gt;"));
  assert.deepEqual(tabela(html, "Tramitações").linhas[0].slice(1), [
    "&lt;i&gt;o&lt;/i&gt;",
    "&lt;script&gt;d&lt;/script&gt;",
  ]);
  for (const bruto of ["<b>t</b>", "<u>e</u>", "<i>o</i>", "<script>d</script>"]) {
    assert.ok(!html.includes(bruto), `HTML bruto na página: ${bruto}`);
  }
});

// --- 404, erro e formato -----------------------------------------------------------------------

test("proposição que a API não conhece é 404", async () => {
  const controle = await pagina();
  assert.equal(controle.status, 200, "controle: a página existe");

  const { status } = await abrir("/camara/proposicoes/4455667/", {
    status: 404,
    corpo: { erro: "não encontrado" },
  });

  assert.equal(status, 404);
});

for (const id of ["0", "01", "abc", "1x", "12345678901"]) {
  test(`id inválido (${id}) é 404 sem chamar a API`, async () => {
    const controle = await pagina();
    assert.equal(controle.status, 200, "controle: a página existe");
    api.chamadas.length = 0;

    const { status } = await abrir(`/camara/proposicoes/${id}/`, { status: 200, corpo: resposta() });

    assert.equal(status, 404);
    assert.deepEqual(api.chamadas, []);
  });
}

test("API com erro dá 500 sem o endereço da API", async () => {
  const { status, html } = await abrir("/camara/proposicoes/4455667/", {
    status: 500,
    corpo: { erro: "falha" },
  });

  assert.equal(status, 500);
  assert.ok(!html.includes(new URL(api.url).host));
});

test("resposta que não é JSON dá 500", async () => {
  const { status } = await abrir("/camara/proposicoes/4455667/", {
    status: 200,
    corpo: "isto não é json",
  });

  assert.equal(status, 500);
});

const foraDoFormato = {
  "proposicao ausente": () => {
    const corpo = resposta();
    delete corpo.proposicao;
    return corpo;
  },
  "proposicao sem título": () => {
    const corpo = resposta();
    corpo.proposicao.titulo = "";
    return corpo;
  },
  "id_camara em texto": () => {
    const corpo = resposta();
    corpo.proposicao.id_camara = "4455667";
    return corpo;
  },
  "ementa vazia em vez de null": () => {
    const corpo = resposta();
    corpo.proposicao.ementa = "";
    return corpo;
  },
  "tramitacoes ausente": () => {
    const corpo = resposta();
    delete corpo.tramitacoes;
    return corpo;
  },
  "tramitacoes que não é lista": () => resposta({ tramitacoes: { a: 1 } }),
  "tramitação sem descrição": () => {
    const item = tramitacao();
    delete item.descricao;
    return resposta({ tramitacoes: [item] });
  },
  "descrição vazia": () => resposta({ tramitacoes: [tramitacao({ descricao: "" })] }),
  "órgão que não é texto": () => resposta({ tramitacoes: [tramitacao({ orgao: 7 })] }),
  "sequência em texto": () => resposta({ tramitacoes: [tramitacao({ sequencia: "1" })] }),
  "sequência ausente (null é 'sem sequência', ausente não)": () => {
    const item = tramitacao();
    delete item.sequencia;
    return resposta({ tramitacoes: [item] });
  },
  "data_hora sem deslocamento": () =>
    resposta({ tramitacoes: [tramitacao({ data_hora: "2026-05-07T16:58:00" })] }),
  "data_hora que não é data": () =>
    resposta({ tramitacoes: [tramitacao({ data_hora: "ontem às três" })] }),
  "tramitações sem a atribuição das tramitações": () =>
    resposta({ atribuicao_das_tramitacoes: null }),
  "sem tramitações mas com a atribuição das tramitações": () => resposta({ tramitacoes: [] }),
  "atribuicao_da_proposicao ausente": () => {
    const corpo = resposta();
    delete corpo.atribuicao_da_proposicao;
    return corpo;
  },
  "atribuicao_da_proposicao nula": () => resposta({ atribuicao_da_proposicao: null }),
  "atribuicao_das_tramitacoes que não é objeto": () =>
    resposta({ atribuicao_das_tramitacoes: "x" }),
};

for (const [nome, montar] of Object.entries(foraDoFormato)) {
  test(`resposta fora do formato é recusada inteira: ${nome}`, async () => {
    const controle = await pagina();
    assert.equal(controle.status, 200, "controle: com o formato certo a página existe");

    const { status, html } = await pagina(montar(), 4455667);

    assert.equal(status, 500);
    assert.ok(!html.includes("Apresentação de Requerimento"));
    assert.ok(!html.includes("PL 11/2003"));
  });
}
