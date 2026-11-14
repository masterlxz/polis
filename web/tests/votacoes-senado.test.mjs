// Votações do Senado (`/senado/votacoes/` e `/senado/votacoes/<codigo>/`, ADR 0029 e 0030), contra o
// servidor de produção e uma API falsa. Dados todos sintéticos. O que mais importa: na votação
// secreta a página nunca mostra "Voto" (só participação), e uma resposta da API que misture as
// formas é recusada inteira; sigla só ganha significado se estiver na legenda medida (Rodada 4 de
// `project/fontes/senado.md`); o resultado A/R aparece com a nota de que é leitura do placar.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

const CAMINHO_DA_LISTA = "/internal/v1/senado/votacoes/";

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
    conjunto: "Votações do Senado",
    coletado_em: "2026-11-13T09:00:00+00:00",
    url_origem: "https://dados.example.org/dadosabertos/votacao.json",
    licenca: { id: null, url: null },
    ...extra,
  };
}

function item(extra = {}) {
  return {
    codigo: 7001,
    data: "2026-11-12",
    identificacao: "PL 1/2026",
    ementa: "Dispõe sobre um assunto de teste.",
    resultado: "A",
    secreta: false,
    ...extra,
  };
}

function lista({ votacoes = [item()], pagina = 1, total_paginas = 1, atribuicao } = {}) {
  return {
    votacoes,
    pagina,
    total_paginas,
    atribuicao: atribuicao === undefined ? atribuicaoPadrao() : atribuicao,
  };
}

function votante(id, nome, sigla, extra = {}) {
  return { id_senado: id, nome, partido: "XYZ", uf: "SP", sigla, ...extra };
}

function votacao(extra = {}) {
  return {
    codigo: 7001,
    data: "2026-11-12",
    sigla: "PL",
    numero: "1",
    ano: 2026,
    identificacao: "PL 1/2026",
    ementa: "Dispõe sobre um assunto de teste.",
    resultado: "A",
    secreta: false,
    id_processo: 100,
    codigo_materia: 200,
    totais_da_fonte: { sim: null, nao: null, abstencao: null },
    ...extra,
  };
}

function aberta({ votos, ...extra } = {}) {
  return {
    votacao: votacao(),
    contagem_por_sigla: { Sim: 2, Não: 1, AP: 1 },
    votos: votos ?? [
      votante(1, "Ana", "Sim"),
      votante(2, "Bruno", "Sim"),
      votante(3, "Carla", "Não"),
      votante(4, "Davi", "AP"),
    ],
    atribuicao: atribuicaoPadrao(),
    ...extra,
  };
}

function secreta(extra = {}) {
  return {
    votacao: votacao({
      codigo: 7002,
      identificacao: "MSF 9/2026",
      secreta: true,
      totais_da_fonte: { sim: 43, nao: 2, abstencao: 1 },
    }),
    contagem_por_sigla: { Votou: 3, AP: 1 },
    participacao: [
      votante(1, "Ana", "Votou"),
      votante(2, "Bruno", "Votou"),
      votante(3, "Carla", "Votou"),
      votante(4, "Davi", "AP"),
    ],
    atribuicao: atribuicaoPadrao(),
    ...extra,
  };
}

async function abrir(caminho, resposta) {
  api.resposta = () => resposta;
  const retorno = await fetch(`${front.base}${caminho}`);
  return { status: retorno.status, html: await retorno.text() };
}

const listaOk = (corpo = lista()) => abrir("/senado/votacoes/", { status: 200, corpo });
const detalhe = (corpo = aberta(), codigo = corpo?.votacao?.codigo ?? 7001) =>
  abrir(`/senado/votacoes/${codigo}/`, { status: 200, corpo });

// --- Lista ---------------------------------------------------------------------------------------

test("lista: identificação, data, ementa, resultado e link para o detalhe", async () => {
  const { status, html } = await listaOk();

  assert.equal(status, 200);
  assert.ok(html.includes("PL 1/2026"));
  assert.ok(html.includes("12/11/2026"));
  assert.ok(html.includes("Dispõe sobre um assunto de teste."));
  assert.ok(html.includes("Aprovada"));
  assert.ok(html.includes('href="/senado/votacoes/7001/"'));
});

test("lista: votação secreta vem marcada, a aberta não", async () => {
  const { html } = await listaOk(
    lista({ votacoes: [item(), item({ codigo: 7002, identificacao: "MSF 9/2026", secreta: true })] }),
  );

  // Conta só na marcação: o payload do React (`self.__next_f`) repete o texto no mesmo HTML.
  assert.equal((html.match(/<span class="detalhe">Votação secreta<\/span>/g) ?? []).length, 1);
});

test("lista: primeira de duas páginas tem 'Próxima' e não tem 'Anterior'", async () => {
  const { html } = await listaOk(lista({ pagina: 1, total_paginas: 2 }));

  assert.ok(html.includes('href="/senado/votacoes/?pagina=2"'));
  assert.ok(html.includes("Próxima"));
  assert.ok(!html.includes("Anterior"));
});

test("lista: última página tem 'Anterior' e não tem 'Próxima'", async () => {
  const { html } = await abrir("/senado/votacoes/?pagina=2", {
    status: 200,
    corpo: lista({ pagina: 2, total_paginas: 2 }),
  });

  assert.ok(html.includes('href="/senado/votacoes/?pagina=1"'));
  assert.ok(html.includes("Anterior"));
  assert.ok(!html.includes("Próxima"));
});

test("lista: a página pedida segue para a API", async () => {
  api.chamadas.length = 0;

  await abrir("/senado/votacoes/?pagina=2", { status: 200, corpo: lista({ pagina: 2, total_paginas: 2 }) });

  assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}?pagina=2`]);
});

for (const invalida of ["abc", "0", "-1", "99999", "1.5", ""]) {
  test(`lista: página inválida vira a primeira: "${invalida}"`, async () => {
    api.chamadas.length = 0;

    const { status } = await abrir(`/senado/votacoes/?pagina=${invalida}`, {
      status: 200,
      corpo: lista(),
    });

    assert.equal(status, 200);
    assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}?pagina=1`]);
  });
}

test("lista: além da última, aviso e link para a primeira", async () => {
  const { status, html } = await abrir("/senado/votacoes/?pagina=9", {
    status: 200,
    corpo: lista({ votacoes: [], pagina: 9, total_paginas: 2, atribuicao: null }),
  });

  assert.equal(status, 200);
  assert.ok(html.includes("Nenhuma votação nesta página"));
  // O menu também aponta para /senado/votacoes/: o teste exige o link com o texto da página.
  assert.match(html, /<a href="\/senado\/votacoes\/">Voltar para a primeira página<\/a>/);
});

test("lista: sem nenhuma votação coletada, aviso e nada de atribuição", async () => {
  const { status, html } = await listaOk(
    lista({ votacoes: [], pagina: 1, total_paginas: 0, atribuicao: null }),
  );

  assert.equal(status, 200);
  assert.ok(html.includes("Nenhuma votação coletada ainda"));
  assert.ok(!html.includes("Origem dos dados"));
});

test("lista: mostra a origem dos dados", async () => {
  const { html } = await listaOk();

  assert.ok(html.includes("Origem dos dados"));
  assert.ok(html.includes("Senado Federal: Dados Abertos"));
  assert.ok(html.includes("Votações do Senado"));
});

test("lista fora do formato (código que não é inteiro): erro 500 sem vazar", async () => {
  const { status, html } = await listaOk(
    lista({ votacoes: [item({ codigo: "../../admin/SEGREDO" })] }),
  );

  assert.equal(status, 500);
  assert.ok(!html.includes("SEGREDO"));
});

test("navegação principal tem o link para as votações do Senado", async () => {
  const { html } = await listaOk();

  assert.match(html, /<nav[^>]*>.*href="\/senado\/votacoes\/"[^>]*>Votações do Senado<\/a>/s);
});

// --- Detalhe: aberta -----------------------------------------------------------------------------

test("detalhe aberto: identificação no h1, data, ementa e 'Aprovada (A)' com a nota do placar", async () => {
  const { status, html } = await detalhe();

  assert.equal(status, 200);
  assert.match(html, /<h1[^>]*>PL 1\/2026<\/h1>/);
  assert.ok(html.includes("12/11/2026"));
  assert.ok(html.includes("Dispõe sobre um assunto de teste."));
  assert.ok(html.includes("Aprovada (A)"));
  assert.ok(html.includes("o polis a lê pelo placar"));
});

test("detalhe: resultado R aparece como 'Rejeitada (R)'", async () => {
  const corpo = aberta();
  corpo.votacao.resultado = "R";

  const { html } = await detalhe(corpo);

  assert.ok(html.includes("Rejeitada (R)"));
  assert.ok(!html.includes("Aprovada"));
});

test("detalhe: resultado desconhecido aparece cru, sem virar aprovada nem rejeitada", async () => {
  const corpo = aberta();
  corpo.votacao.resultado = "X";

  const { status, html } = await detalhe(corpo);

  assert.equal(status, 200);
  assert.ok(!html.includes("Aprovada") && !html.includes("Rejeitada"));
  assert.match(html, />X</);
});

test("detalhe aberto: tabela com a coluna 'Voto' e a linha de cada senador", async () => {
  const { html } = await detalhe();

  assert.match(html, /<th[^>]*>Voto<\/th>/);
  assert.match(html, /<td>Ana<\/td><td>XYZ<\/td><td>SP<\/td><td>Sim<\/td>/);
});

test("detalhe aberto: contagem rotulada como do polis", async () => {
  const { html } = await detalhe();

  assert.ok(html.includes("contado pelo polis a partir dos votos"));
});

test("sigla da legenda medida aparece por extenso, com a sigla ao lado", async () => {
  const { html } = await detalhe();

  assert.ok(html.includes("Atividade parlamentar (AP)"));
});

test("sigla fora da legenda aparece crua, com a nota de que não foi verificada", async () => {
  const controle = await detalhe();
  assert.ok(!controle.html.includes("não verificou o significado"), "controle: sem sigla nova, sem nota");

  const { html } = await detalhe(aberta({ votos: [votante(1, "Ana", "ZZ-NOVA")] }));

  assert.match(html, /<td>ZZ-NOVA<\/td>/);
  assert.ok(html.includes("não verificou o significado"));
});

test("'S/Partido' aparece como 'Sem partido'", async () => {
  const { html } = await detalhe(aberta({ votos: [votante(1, "Ana", "Sim", { partido: "S/Partido" })] }));

  assert.ok(html.includes("Sem partido"));
  assert.ok(!html.includes("S/Partido"));
});

test("partido nulo deixa a célula vazia, sem 'null'", async () => {
  const { html } = await detalhe(aberta({ votos: [votante(1, "Ana", "Sim", { partido: null })] }));

  assert.match(html, /<td>Ana<\/td><td><\/td><td>SP<\/td>/);
  assert.ok(!html.includes(">null<"));
});

test("nome com HTML aparece escapado", async () => {
  const { status, html } = await detalhe(
    aberta({ votos: [votante(1, "<script>alert(1)</script>", "Sim")] }),
  );

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("<script>alert(1)</script>"));
  assert.ok(html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));
});

test("detalhe: mostra a origem dos dados", async () => {
  const { html } = await detalhe();

  assert.ok(html.includes("Origem dos dados"));
  assert.ok(html.includes("Votações do Senado"));
});

// --- Detalhe: secreta ----------------------------------------------------------------------------

test("secreta: aviso, total do Senado e tabela de participação sem coluna 'Voto'", async () => {
  const { status, html } = await detalhe(secreta());

  assert.equal(status, 200);
  assert.ok(html.includes("o Senado não divulga o voto de cada senador"));
  assert.ok(html.includes("Participação"));
  assert.match(html, /<th[^>]*>Situação<\/th>/);
  assert.ok(!/<th[^>]*>Voto<\/th>/.test(html), "a secreta tem coluna 'Voto'");
  assert.ok(html.includes("total informado pelo Senado"));
  assert.match(html, /<td>Sim<\/td><td>43<\/td>/);
});

test("secreta: 'Votou' aparece como participação, nunca sozinho como se fosse voto", async () => {
  const { html } = await detalhe(secreta());

  assert.ok(html.includes("Votou (voto secreto)"));
  assert.ok(!/<td>Votou<\/td>/.test(html));
});

const misturadas = {
  "secreta com 'votos'": () => {
    const corpo = secreta();
    corpo.votos = corpo.participacao;
    delete corpo.participacao;
    return corpo;
  },
  "aberta com 'participacao'": () => {
    const corpo = aberta();
    corpo.participacao = corpo.votos;
    delete corpo.votos;
    return corpo;
  },
  "as duas chaves": () => ({ ...secreta(), votos: secreta().participacao }),
  "nenhuma das chaves": () => {
    const corpo = aberta();
    delete corpo.votos;
    return corpo;
  },
};

for (const [nome, montar] of Object.entries(misturadas)) {
  test(`resposta que mistura as formas é recusada inteira: ${nome}`, async () => {
    const { status, html } = await detalhe(montar());

    assert.equal(status, 500);
    assert.ok(!html.includes("Ana"));
  });
}

// --- Detalhe: erros e estrutura ------------------------------------------------------------------

for (const invalido of ["abc", "0x1", "1234567890", "70-01", "-1"]) {
  test(`código malformado dá 404 sem chamar a API: ${invalido}`, async () => {
    const controle = await detalhe();
    assert.equal(controle.status, 200, "controle: a página precisa existir");
    const antes = api.chamadas.length;

    const { status } = await abrir(`/senado/votacoes/${invalido}/`, { status: 200, corpo: aberta() });

    assert.equal(status, 404);
    assert.equal(api.chamadas.length, antes, "chamou a API com um código inválido");
  });
}

test("código válido: a API recebe exatamente GET /internal/v1/senado/votacoes/<codigo>/", async () => {
  api.chamadas.length = 0;

  await detalhe();

  assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}7001/`]);
});

test("API responde 404: página 404 em português", async () => {
  const controle = await detalhe();
  assert.equal(controle.status, 200, "controle: sem a rota, o 404 viria do Next e não da API");
  api.chamadas.length = 0;

  const { status, html } = await abrir("/senado/votacoes/7001/", {
    status: 404,
    corpo: { erro: "não encontrado" },
  });

  assert.equal(status, 404);
  assert.match(html, /não encontrad/i);
  assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}7001/`], "a API não foi chamada");
});

test("API responde 500: erro genérico, sem o endereço da API", async () => {
  const { status, html } = await abrir("/senado/votacoes/7001/", { status: 500, corpo: { erro: "boom" } });

  assert.equal(status, 500);
  assert.ok(!html.includes(new URL(api.url).host));
});

test("estrutura: um h1, título com o descritor e noindex", async () => {
  for (const { status, html } of [await listaOk(), await detalhe()]) {
    assert.equal(status, 200, "controle: a 404 do Next também tem h1, título e noindex");
    assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1);
    assert.match(html, /<title>[^<]*transparência e inteligência cívica[^<]*<\/title>/);
    assert.match(html, /<meta name="robots" content="noindex/);
  }
});
