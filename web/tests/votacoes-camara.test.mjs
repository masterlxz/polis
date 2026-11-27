// Votações da Câmara (`/camara/votacoes/` e `/camara/votacoes/<id>/`, ADR 0031 e 0032), contra o
// servidor de produção e uma API falsa. Dados todos sintéticos. O que mais importa: `0/0/0` nos
// totais da fonte não é contagem e nunca aparece como resultado; `voto` nulo é "sem posição
// registrada" (nunca vazio nem "null"); `aprovacao` e as siglas de voto saem como a fonte as manda,
// com a legenda da documentação da Câmara; o link do nome só existe com `tem_perfil`; as
// duas atribuições (votação e votos) são citadas à parte; e uma resposta fora do formato derruba a
// página sem vazar o texto dela.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

const CAMINHO_DA_LISTA = "/internal/v1/camara/votacoes/";
// A legenda copia o que a documentação oficial diz, lida em 2026-11-26 em
// https://dadosabertos.camara.leg.br/howtouse/2020-02-07-dados-votacoes.html: `aprovacao` 1 é
// "resultou em aprovação", 0 é "não foi aprovada" (rejeitada ou sem quórum), vazio é "não é possível
// afirmar"; `votosOutros` junta abstenções, obstrução e "Art. 17" (abstenção obrigatória do
// presidente, em referência ao Regimento da Câmara).
const LEGENDA_DA_APROVACAO =
  "Aprovação, segundo a documentação da Câmara: 1 é votação que resultou em aprovação; 0, proposição não aprovada (rejeitada ou sem quórum); sem código, a Câmara não afirma o resultado.";
const LEGENDA_DAS_SIGLAS =
  "Votos: Abstenção, Obstrução (o parlamentar se abstém e não quer ser contado no quórum) e Artigo 17 (abstenção obrigatória do presidente, em referência ao Regimento da Câmara) entram em “outros” nos totais da Câmara.";
const LINK_DA_DOCUMENTACAO =
  '<a href="https://dadosabertos.camara.leg.br/howtouse/2020-02-07-dados-votacoes.html">documentação da Câmara</a>';
const PREFIXO_DA_NOTA = "Códigos como a fonte os manda.";

// A nota inteira (prefixo, as legendas que couberem e o link) ou nada: o que a página não mostra não
// pode deixar nem o prefixo nem o link da documentação, e o "não foi verificado" antigo não volta.
function semNota(html) {
  assert.ok(!html.includes(PREFIXO_DA_NOTA), "prefixo da nota fora de hora");
  assert.ok(!html.includes(LINK_DA_DOCUMENTACAO), "link da documentação fora de hora");
  assert.ok(!html.includes(LEGENDA_DA_APROVACAO) && !html.includes(LEGENDA_DAS_SIGLAS));
  assert.ok(!html.includes("não foi verificado"));
}

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

function atribuicaoDasVotacoes(extra = {}) {
  return {
    fonte: "Câmara dos Deputados: Dados Abertos",
    conjunto: "Votações da Câmara (2026)",
    coletado_em: "2026-11-25T18:00:00+00:00",
    url_origem: "https://dados.example.org/arquivos/votacoes/csv/votacoes-2026.csv",
    licenca: { id: null, url: null },
    ...extra,
  };
}

function atribuicaoDosVotos(extra = {}) {
  return {
    fonte: "Câmara dos Deputados: Dados Abertos",
    conjunto: "Votos nominais da Câmara (2026)",
    coletado_em: "2026-11-25T18:05:00+00:00",
    url_origem: "https://dados.example.org/arquivos/votacoesVotos/csv/votacoesVotos-2026.csv",
    licenca: { id: null, url: null },
    ...extra,
  };
}

function atribuicaoDasProposicoes(extra = {}) {
  return {
    fonte: "Câmara dos Deputados: Dados Abertos",
    conjunto: "Proposições das votações da Câmara (2026)",
    coletado_em: "2026-11-25T18:10:00+00:00",
    url_origem: "https://dados.example.org/arquivos/votacoesProposicoes/csv/votacoesProposicoes-2026.csv",
    licenca: { id: null, url: null },
    ...extra,
  };
}

// Uma proposição do detalhe (ADR 0032, emenda 5). `id_camara` é um número que não aparece em
// nenhuma outra parte da fixture: a página não o mostra (não há rota para a proposição).
function proposicao(extra = {}) {
  return {
    id_camara: 4455667,
    titulo: "PL 9001/2026",
    tipo: "PL",
    numero: 9001,
    ano: 2026,
    ementa: "Ementa A",
    origem: "proposicoes",
    ...extra,
  };
}

function totais(sim = 0, nao = 0, outros = 0) {
  return { sim, nao, outros };
}

// O item da lista. `id_proposicao` é um número que não aparece em nenhuma outra parte da fixture.
function itemDaLista(extra = {}) {
  return {
    id: "2332174-59",
    data: "2026-11-24",
    orgao: "PLEN",
    aprovacao: "1",
    totais_da_fonte: totais(),
    descricao: "Aprovado o requerimento de teste.",
    id_proposicao: 2659321,
    tem_votos_nominais: false,
    ...extra,
  };
}

function lista({ votacoes = [itemDaLista()], pagina = 1, total_paginas = 1, atribuicao } = {}) {
  return {
    votacoes,
    pagina,
    total_paginas,
    atribuicao: atribuicao === undefined ? atribuicaoDasVotacoes() : atribuicao,
  };
}

function voto(idCamara, nome, partido, valor, extra = {}) {
  return {
    legislatura: 57,
    id_camara: idCamara,
    partido,
    voto: valor,
    tem_perfil: nome !== null,
    nome,
    ...extra,
  };
}

// A votação do detalhe: os campos do item da lista, sem `tem_votos_nominais`.
function votacaoDoDetalhe(extra = {}) {
  const { tem_votos_nominais: _, ...campos } = itemDaLista();
  return { ...campos, ...extra };
}

// Quatro votos: Sim ×2, Não ×1 e sem posição ×1 (contagens diferentes entre si), dois com perfil e
// dois sem, e partidos e siglas que não coincidem com nada mais da fixture.
function nominal(extra = {}) {
  return {
    votacao: votacaoDoDetalhe({ totais_da_fonte: totais(2, 1, 1) }),
    votos: [
      voto(154178, "Ana Souza", "ABC", "Sim"),
      voto(200, null, "DEF", "Não"),
      voto(154179, "Carla Dias", null, null),
      voto(300, null, "ABC", "Artigo 17"),
    ],
    contagem_por_voto: [
      { voto: "Sim", quantidade: 2 },
      { voto: "Não", quantidade: 1 },
      { voto: null, quantidade: 1 },
    ],
    atribuicao: atribuicaoDasVotacoes(),
    atribuicao_dos_votos: atribuicaoDosVotos(),
    proposicoes: [],
    atribuicao_das_proposicoes: null,
    ...extra,
  };
}

function semVotos(extra = {}) {
  return {
    votacao: votacaoDoDetalhe(),
    votos: [],
    contagem_por_voto: [],
    atribuicao: atribuicaoDasVotacoes(),
    atribuicao_dos_votos: null,
    proposicoes: [],
    atribuicao_das_proposicoes: null,
    ...extra,
  };
}

async function abrir(caminho, resposta) {
  api.resposta = () => resposta;
  const retorno = await fetch(`${front.base}${caminho}`);
  return { status: retorno.status, html: await retorno.text() };
}

const listaOk = (corpo = lista()) => abrir("/camara/votacoes/", { status: 200, corpo });
const detalhe = (corpo = nominal(), id = corpo?.votacao?.id ?? "2332174-59") =>
  abrir(`/camara/votacoes/${id}/`, { status: 200, corpo });

// Conta só na marcação: o payload do React (`self.__next_f`) repete o texto no mesmo HTML.
function contar(html, padrao) {
  return (html.match(padrao) ?? []).length;
}

// A tabela cuja legenda (`<caption>`) é `legenda`: cabeçalho e linhas, cada célula em texto, com o
// link virando "[texto](href)". `null` se não existe.
function tabela(html, legenda) {
  const corpo = Array.from(html.matchAll(/<table[^>]*>(.*?)<\/table>/gs), (achado) => achado[1]).find(
    (conteudo) => conteudo.includes(`<caption>${legenda}</caption>`),
  );
  if (corpo === undefined) return null;
  const texto = (celula) =>
    celula.replace(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/s, "[$2]($1)");
  const celulas = (linha, marca) =>
    Array.from(linha.matchAll(new RegExp(`<${marca}[^>]*>(.*?)</${marca}>`, "gs")), (achado) =>
      texto(achado[1]),
    );
  const linhas = Array.from(corpo.matchAll(/<tr[^>]*>(.*?)<\/tr>/gs), (achado) => achado[1]);
  return {
    cabecalho: linhas.flatMap((linha) => celulas(linha, "th")),
    linhas: linhas.map((linha) => celulas(linha, "td")).filter((celulas) => celulas.length > 0),
  };
}

// --- Lista ---------------------------------------------------------------------------------------

test("lista: data e órgão no link, descrição e a marca de voto nominal de cada votação", async () => {
  const { status, html } = await listaOk(
    lista({
      votacoes: [
        itemDaLista({ tem_votos_nominais: true }),
        itemDaLista({
          id: "2332175-1",
          data: "2026-11-23",
          orgao: "CCJC",
          descricao: "Rejeitado o destaque de teste.",
          tem_votos_nominais: false,
        }),
      ],
    }),
  );

  assert.equal(status, 200);
  assert.match(html, /<a href="\/camara\/votacoes\/2332174-59\/"[^>]*>24\/11\/2026 · PLEN<\/a>/);
  assert.match(html, /<a href="\/camara\/votacoes\/2332175-1\/"[^>]*>23\/11\/2026 · CCJC<\/a>/);
  assert.ok(html.includes("Aprovado o requerimento de teste."));
  assert.ok(html.includes("Rejeitado o destaque de teste."));
  // Cada marca fica no item certo: contar as ocorrências não pegaria as duas trocadas de lugar.
  // O trecho vai só até o `</li>`: o último iria até o fim da página, e o payload do React
  // (`self.__next_f`) repete o texto da lista inteira.
  const itens = html.split("<li").map((trecho) => trecho.split("</li>")[0]);
  const itemComNominais = itens.find((trecho) => trecho.includes("/2332174-59/"));
  const itemSemNominais = itens.find((trecho) => trecho.includes("/2332175-1/"));
  assert.ok(itemComNominais?.includes('<span class="detalhe">Com votos nominais</span>'));
  assert.ok(itemSemNominais?.includes('<span class="detalhe">Sem votos nominais</span>'));
  assert.ok(!itemComNominais.includes("Sem votos nominais"));
  assert.ok(!itemSemNominais.includes("Com votos nominais"));
  assert.ok(!html.includes("Só os totais da fonte"), "a lista não promete totais que o detalhe oculta");
});

// Dois links "24/11/2026 · PLEN" seguidos são indistinguíveis numa lista de links de leitor de tela;
// o que os distingue é a ementa, que fica fora do link. `aria-describedby` a liga ao link sem mudar
// o que se vê.
test("lista: o link aponta (aria-describedby) para a ementa da própria votação", async () => {
  const { status, html } = await listaOk(
    lista({
      votacoes: [
        itemDaLista({ descricao: "Primeira ementa." }),
        itemDaLista({ id: "2332175-1", descricao: "Segunda ementa." }),
      ],
    }),
  );

  assert.equal(status, 200);
  const itens = html.split("<li").map((trecho) => trecho.split("</li>")[0]);
  const descrito = (id, ementa) => {
    const item = itens.find((trecho) => trecho.includes(`/camara/votacoes/${id}/`));
    const alvo = item?.match(/<a [^>]*aria-describedby="([^"]+)"/)?.[1];
    assert.ok(alvo, `o link de ${id} precisa de aria-describedby`);
    assert.ok(
      item.includes(`<p class="ementa" id="${alvo}">${ementa}</p>`),
      `o id ${alvo} é o da ementa de ${id}`,
    );
    return alvo;
  };
  const primeiro = descrito("2332174-59", "Primeira ementa.");
  const segundo = descrito("2332175-1", "Segunda ementa.");
  assert.notEqual(primeiro, segundo, "cada votação tem o seu id de ementa");
  assert.equal(html.split(`id="${primeiro}"`).length - 1, 1, "o id aparece uma vez só");
});

test("lista: sem ementa, o link não aponta para um id que não existe", async () => {
  const { status, html } = await listaOk(lista({ votacoes: [itemDaLista({ descricao: "" })] }));

  assert.equal(status, 200);
  // Só a tag do link conta: o payload do React (`self.__next_f`) lista `aria-describedby` como
  // `$undefined` mesmo quando o atributo não sai no HTML.
  const link = html.match(/<a [^>]*href="\/camara\/votacoes\/2332174-59\/"[^>]*>/)?.[0];
  assert.ok(link, "controle: o link existe");
  assert.ok(!link.includes("aria-describedby"));
  assert.ok(!html.includes('<p class="ementa"'));
});

test("lista: o id da proposição não aparece (0 é sentinela de 'sem proposição')", async () => {
  const { status, html } = await listaOk(
    lista({
      votacoes: [itemDaLista(), itemDaLista({ id: "9-9", id_proposicao: 0 })],
    }),
  );

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("2659321"));
});

test("lista: descrição com HTML aparece escapada", async () => {
  const { status, html } = await listaOk(
    lista({ votacoes: [itemDaLista({ descricao: "<script>alert(1)</script>" })] }),
  );

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("<script>alert(1)</script>"));
  assert.ok(html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));
});

test("lista: primeira de duas páginas tem 'Próxima' e não tem 'Anterior'", async () => {
  const { html } = await listaOk(lista({ pagina: 1, total_paginas: 2 }));

  assert.ok(html.includes('href="/camara/votacoes/?pagina=2"'));
  assert.ok(html.includes("Próxima"));
  assert.ok(!html.includes("Anterior"));
});

test("lista: última página tem 'Anterior' e não tem 'Próxima'", async () => {
  const { html } = await abrir("/camara/votacoes/?pagina=2", {
    status: 200,
    corpo: lista({ pagina: 2, total_paginas: 2 }),
  });

  assert.ok(html.includes('href="/camara/votacoes/?pagina=1"'));
  assert.ok(html.includes("Anterior"));
  assert.ok(!html.includes("Próxima"));
});

test("lista: no meio de três páginas, as duas setas e 'Página 2 de 3'", async () => {
  const { html } = await abrir("/camara/votacoes/?pagina=2", {
    status: 200,
    corpo: lista({ pagina: 2, total_paginas: 3 }),
  });

  assert.ok(html.includes('href="/camara/votacoes/?pagina=1"'));
  assert.ok(html.includes('href="/camara/votacoes/?pagina=3"'));
  assert.ok(html.includes("Página 2 de 3"));
});

test("lista: a página pedida segue para a API", async () => {
  api.chamadas.length = 0;

  await abrir("/camara/votacoes/?pagina=2", { status: 200, corpo: lista({ pagina: 2, total_paginas: 2 }) });

  assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}?pagina=2`]);
});

test("lista: página de 4 dígitos (a maior) segue para a API", async () => {
  api.chamadas.length = 0;

  await abrir("/camara/votacoes/?pagina=9999", { status: 200, corpo: lista({ pagina: 9999 }) });

  assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}?pagina=9999`]);
});

// A regra do `?pagina=` é `[1-9][0-9]{0,3}` (a mesma do Senado e da API): o resto vira a página 1 e a
// API nunca vê o 400. "٢" (2 em dígito árabe-índico) é guarda de regressão: o `[0-9]` já o recusa.
for (const invalida of ["abc", "0", "-1", "99999", "1.5", "", "02", "٢"]) {
  test(`lista: página inválida vira a primeira: "${invalida}"`, async () => {
    api.chamadas.length = 0;

    const { status } = await abrir(`/camara/votacoes/?pagina=${invalida}`, {
      status: 200,
      corpo: lista(),
    });

    assert.equal(status, 200);
    assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}?pagina=1`]);
  });
}

test("lista: além da última, aviso e link para a primeira, sem setas", async () => {
  const { status, html } = await abrir("/camara/votacoes/?pagina=9", {
    status: 200,
    corpo: lista({ votacoes: [], pagina: 9, total_paginas: 2, atribuicao: null }),
  });

  assert.equal(status, 200);
  assert.ok(html.includes("Nenhuma votação nesta página"));
  // O menu também aponta para /camara/votacoes/: o teste exige o link com o texto da página.
  assert.match(html, /<a href="\/camara\/votacoes\/">Voltar para a primeira página<\/a>/);
  assert.ok(!html.includes("Anterior"));
  assert.ok(!html.includes("Próxima"));
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
  assert.ok(html.includes("Câmara dos Deputados: Dados Abertos"));
  assert.ok(html.includes("Votações da Câmara (2026)"));
});

test("navegação principal tem os links das votações da Câmara e do Senado", async () => {
  const { html } = await listaOk();

  assert.match(html, /<nav[^>]*>.*href="\/camara\/votacoes\/"[^>]*>Votações da Câmara<\/a>/s);
  assert.match(html, /<nav[^>]*>.*href="\/senado\/votacoes\/"[^>]*>Votações do Senado<\/a>/s);
});

const listasFora = {
  "id que não é texto": () => lista({ votacoes: [itemDaLista({ id: 2332174 })] }),
  "tem_votos_nominais que não é booleano": () =>
    lista({ votacoes: [itemDaLista({ tem_votos_nominais: "sim" })] }),
  "sem tem_votos_nominais": () => {
    const sem = itemDaLista();
    delete sem.tem_votos_nominais;
    return lista({ votacoes: [sem] });
  },
  "data que não é texto": () => lista({ votacoes: [itemDaLista({ data: 20261124 })] }),
  "órgão ausente": () => {
    const sem = itemDaLista();
    delete sem.orgao;
    return lista({ votacoes: [sem] });
  },
  "descrição que não é texto": () => lista({ votacoes: [itemDaLista({ descricao: null })] }),
  "aprovacao que não é texto nem nulo": () => lista({ votacoes: [itemDaLista({ aprovacao: 1 })] }),
  "totais sem 'outros'": () =>
    lista({ votacoes: [itemDaLista({ totais_da_fonte: { sim: 1, nao: 1 } })] }),
  "totais com texto": () =>
    lista({ votacoes: [itemDaLista({ totais_da_fonte: totais("1", 0, 0) })] }),
  "id_proposicao que não é inteiro": () =>
    lista({ votacoes: [itemDaLista({ id_proposicao: "0" })] }),
  "id com formato que a rota não aceita (vira href)": () =>
    lista({ votacoes: [itemDaLista({ id: "../x" })] }),
  "id com parâmetro de consulta (vira href)": () =>
    lista({ votacoes: [itemDaLista({ id: "1-2?a=b" })] }),
  "total_paginas que não é inteiro": () => lista({ total_paginas: "2" }),
  "pagina que não é inteiro": () => lista({ pagina: "1" }),
  "votacoes que não é lista": () => ({ ...lista(), votacoes: { a: 1 } }),
  "atribuicao que não é objeto": () => lista({ atribuicao: "x" }),
};

for (const [nome, montar] of Object.entries(listasFora)) {
  test(`lista fora do formato é recusada inteira: ${nome}`, async () => {
    const controle = await listaOk();
    assert.equal(controle.status, 200, "controle: com o formato certo a página existe");

    const { status, html } = await listaOk(montar());

    assert.equal(status, 500);
    assert.ok(!html.includes("Aprovado o requerimento de teste."));
  });
}

test("lista: API com erro dá 500 sem o endereço da API", async () => {
  const { status, html } = await abrir("/camara/votacoes/", { status: 500, corpo: { erro: "boom" } });

  assert.equal(status, 500);
  assert.ok(!html.includes(new URL(api.url).host));
});

test("lista: resposta que não é JSON dá 500", async () => {
  const { status } = await abrir("/camara/votacoes/", { status: 200, corpo: "isto não é JSON" });

  assert.equal(status, 500);
});

// --- Detalhe: votos nominais ---------------------------------------------------------------------

test("detalhe: h1 com data e órgão, descrição, e a aprovação como código da fonte", async () => {
  const { status, html } = await detalhe();

  assert.equal(status, 200);
  assert.match(html, /<h1[^>]*>Votação de 24\/11\/2026 · PLEN<\/h1>/);
  assert.match(html, /<p class="ementa">Aprovado o requerimento de teste\.<\/p>/);
  assert.match(html, /<dt>Aprovação \(código da fonte\)<\/dt><dd>1<\/dd>/);
  assert.ok(html.includes(LEGENDA_DA_APROVACAO));
  assert.ok(!html.includes("Resultado"), "o código da fonte não é um 'Resultado'");
});

test("detalhe: a legenda cita a documentação da Câmara com link, e o texto antigo some", async () => {
  const { html } = await detalhe();

  assert.ok(html.includes(PREFIXO_DA_NOTA));
  assert.ok(html.includes(LINK_DA_DOCUMENTACAO));
  assert.ok(!html.includes("não foi verificado"), "a nota antiga não pode ficar ao lado da legenda");
});

test("detalhe com voto nominal e aprovação: a nota traz a legenda da aprovação e a das siglas", async () => {
  const { html } = await detalhe();

  assert.ok(html.includes(LEGENDA_DA_APROVACAO));
  assert.ok(html.includes(LEGENDA_DAS_SIGLAS));
});

test("detalhe sem voto nominal e com aprovação: só a legenda da aprovação (não há siglas na página)", async () => {
  const { html } = await detalhe(semVotos());

  assert.ok(html.includes(LEGENDA_DA_APROVACAO));
  assert.ok(!html.includes(LEGENDA_DAS_SIGLAS));
});

test("detalhe com voto nominal e sem aprovação: só a legenda das siglas (não há código de aprovação)", async () => {
  const { html } = await detalhe(nominal({ votacao: votacaoDoDetalhe({ aprovacao: null }) }));

  assert.ok(html.includes(LEGENDA_DAS_SIGLAS));
  assert.ok(!html.includes(LEGENDA_DA_APROVACAO));
});

test("detalhe: o id da proposição não aparece", async () => {
  const { status, html } = await detalhe();

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("2659321"));
});

test("detalhe: tabela de votos com Nome, Partido e Voto, cada dado na sua coluna", async () => {
  const { html } = await detalhe();

  const votos = tabela(html, "Votos");
  assert.ok(votos, "não achei a tabela de votos");
  assert.deepEqual(votos.cabecalho, ["Nome", "Partido", "Voto"]);
  assert.deepEqual(votos.linhas, [
    ["[Ana Souza](/deputados/57-154178/)", "ABC", "Sim"],
    ["Deputado sem perfil (id 200)", "DEF", "Não"],
    ["[Carla Dias](/deputados/57-154179/)", "", "Sem posição registrada"],
    ["Deputado sem perfil (id 300)", "ABC", "Artigo 17"],
  ]);
});

test("detalhe: voto nulo aparece como 'Sem posição registrada', nunca vazio nem 'null'", async () => {
  const { html } = await detalhe();

  assert.ok(html.includes("Sem posição registrada"));
  assert.ok(!html.includes(">null<"));
});

test("detalhe: o link do nome só existe quando a API diz que há perfil", async () => {
  const { status, html } = await detalhe();

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(html.includes('href="/deputados/57-154178/"'));
  assert.ok(!html.includes('href="/deputados/57-200/"'));
  assert.ok(!html.includes('href="/deputados/57-300/"'));
});

test("detalhe: a legislatura do voto vai no link do perfil", async () => {
  const { html } = await detalhe(
    nominal({ votos: [voto(154178, "Ana Souza", "ABC", "Sim", { legislatura: 56 })] }),
  );

  assert.ok(html.includes('href="/deputados/56-154178/"'));
  assert.ok(!html.includes('href="/deputados/57-154178/"'));
});

test("detalhe: contagem por voto, rotulada como do polis, com 'Sem posição registrada'", async () => {
  const { html } = await detalhe();

  const contagem = tabela(html, "Contagem por voto, contado pelo polis a partir dos votos");
  assert.ok(contagem, "não achei a tabela de contagem");
  assert.deepEqual(contagem.cabecalho, ["Voto", "Deputados"]);
  assert.deepEqual(contagem.linhas, [
    ["Sim", "2"],
    ["Não", "1"],
    ["Sem posição registrada", "1"],
  ]);
});

test("detalhe: sigla de voto sai crua, e a legenda das siglas aparece mesmo sem aprovação", async () => {
  const { html } = await detalhe(nominal({ votacao: votacaoDoDetalhe({ aprovacao: null }) }));

  assert.match(html, /<td>Artigo 17<\/td>/);
  assert.ok(html.includes(LEGENDA_DAS_SIGLAS), "com voto nominal a legenda aparece");
});

test("detalhe: nome com HTML aparece escapado", async () => {
  const { status, html } = await detalhe(
    nominal({ votos: [voto(1, "<script>alert(1)</script>", "ABC", "Sim")] }),
  );

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("<script>alert(1)</script>"));
  assert.ok(html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));
});

test("detalhe: descrição com HTML aparece escapada", async () => {
  const { status, html } = await detalhe(
    nominal({ votacao: votacaoDoDetalhe({ descricao: "<b>x</b>" }) }),
  );

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.ok(!html.includes("<b>x</b>"));
  assert.ok(html.includes("&lt;b&gt;x&lt;/b&gt;"));
});

test("detalhe: cita a origem da votação e a dos votos, cada uma com o seu conjunto", async () => {
  const { html } = await detalhe();

  assert.equal(contar(html, /aria-label="Origem dos dados"/g), 2);
  assert.ok(html.includes("Votações da Câmara (2026)"));
  assert.ok(html.includes("Votos nominais da Câmara (2026)"));
});

// --- Detalhe: proposições da votação (ADR 0032, emenda 5; ADR 0033) ------------------------------

// Cada item da lista `<ul class="proposicoes">`: título em `<strong>`, ementa visível no primeiro
// `<p class="ementa">` (ou `null`) e, quando a ementa é longa, o texto inteiro dentro do `<details>`
// (`completa`, senão `null`). Conta só na marcação, que é onde a página decide o que mostrar.
function proposicoesNaPagina(html) {
  const lista = html.match(/<ul class="proposicoes">(.*?)<\/ul>/s)?.[1];
  if (lista === undefined) return null;
  return Array.from(lista.matchAll(/<li[^>]*>(.*?)<\/li>/gs), ([, item]) => ({
    titulo: item.match(/<strong>(.*?)<\/strong>/s)?.[1] ?? null,
    ementa: item.match(/<p class="ementa">(.*?)<\/p>/s)?.[1] ?? null,
    completa: item.match(/<details[^>]*>.*?<p class="ementa">(.*?)<\/p>/s)?.[1] ?? null,
  }));
}

function comProposicoes(itens, extra = {}) {
  return nominal({
    proposicoes: itens,
    atribuicao_das_proposicoes: atribuicaoDasProposicoes(),
    ...extra,
  });
}

test("detalhe: cada proposição com título e ementa, na ordem que a API manda", async () => {
  const { status, html } = await detalhe(
    comProposicoes([
      proposicao({ titulo: "PL 9001/2026", ementa: "Ementa A" }),
      proposicao({ id_camara: 4455668, titulo: "PEC 7/2025", ementa: "Ementa B" }),
    ]),
  );

  assert.equal(status, 200);
  assert.match(html, /<h2>Proposições<\/h2>/);
  assert.deepEqual(proposicoesNaPagina(html), [
    { titulo: "PL 9001/2026", ementa: "Ementa A", completa: null },
    { titulo: "PEC 7/2025", ementa: "Ementa B", completa: null },
  ]);
});

test("detalhe: a origem das proposições ('proposicoes' ou 'objetos') não aparece como rótulo", async () => {
  const { html } = await detalhe(
    comProposicoes([
      proposicao({ origem: "proposicoes" }),
      proposicao({ id_camara: 4455668, titulo: "PL 5/2026", origem: "objetos" }),
    ]),
  );

  assert.equal(proposicoesNaPagina(html).length, 2, "controle: a lista existe");
  // "objetos" só existe na fixture como valor de `origem`; "proposicoes" também é o nome da classe
  // da lista, então só o primeiro prova a ausência.
  assert.ok(!html.includes("objetos"));
});

test("detalhe sem proposições: nenhuma seção, nenhum título e só as outras atribuições", async () => {
  const { status, html } = await detalhe(nominal());

  assert.equal(status, 200);
  assert.equal(proposicoesNaPagina(html), null);
  assert.ok(!html.includes("<h2>Proposições</h2>"));
  assert.equal(contar(html, /aria-label="Origem dos dados"/g), 2);
  assert.ok(!html.includes("Proposições das votações da Câmara (2026)"));
});

test("detalhe: ementa nula sai só com o título, sem parágrafo vazio nem 'null'", async () => {
  const { html } = await detalhe(comProposicoes([proposicao({ ementa: null })]));

  assert.deepEqual(proposicoesNaPagina(html), [
    { titulo: "PL 9001/2026", ementa: null, completa: null },
  ]);
});

test("detalhe: ano nulo é aceito e o título sai como a fonte o manda", async () => {
  const { status, html } = await detalhe(
    comProposicoes([proposicao({ titulo: "PL 9001", ano: null })]),
  );

  assert.equal(status, 200);
  assert.deepEqual(proposicoesNaPagina(html), [
    { titulo: "PL 9001", ementa: "Ementa A", completa: null },
  ]);
});

test("detalhe: título e ementa com HTML aparecem escapados", async () => {
  const { html } = await detalhe(
    comProposicoes([proposicao({ titulo: "<b>t</b>", ementa: "<script>e</script>" })]),
  );

  assert.deepEqual(proposicoesNaPagina(html), [
    { titulo: "&lt;b&gt;t&lt;/b&gt;", ementa: "&lt;script&gt;e&lt;/script&gt;", completa: null },
  ]);
  assert.ok(!html.includes("<b>t</b>"));
});

// --- Detalhe: ementa longa recolhida e lugar da seção (decisão do dono, 2026-11-27) --------------

// Mais de 300 caracteres: o resumo (300 primeiros, sem espaço no fim, mais "…") fica visível e o
// texto inteiro vai num `<details>` nativo, sem JavaScript. Até 300, a ementa sai inteira.
const LIMITE_DA_EMENTA = 300;

// Uma ementa de `tamanho` caracteres, sem espaço e sem acento, para o corte cair onde se espera.
const ementaDe = (tamanho) => "a".repeat(tamanho);

test("detalhe: ementa de exatamente 300 caracteres sai inteira, sem details", async () => {
  const ementa = ementaDe(LIMITE_DA_EMENTA);

  const { html } = await detalhe(comProposicoes([proposicao({ ementa })]));

  assert.deepEqual(proposicoesNaPagina(html), [{ titulo: "PL 9001/2026", ementa, completa: null }]);
  assert.ok(!html.includes("<details"));
});

test("detalhe: ementa de 301 caracteres mostra os 300 primeiros e '…', e a inteira no details", async () => {
  const ementa = ementaDe(LIMITE_DA_EMENTA + 1);

  const { html } = await detalhe(comProposicoes([proposicao({ ementa })]));

  assert.deepEqual(proposicoesNaPagina(html), [
    { titulo: "PL 9001/2026", ementa: `${ementaDe(LIMITE_DA_EMENTA)}…`, completa: ementa },
  ]);
  assert.match(html, /<summary>Ler a ementa inteira<\/summary>/);
});

test("detalhe: ementa de 2.500 caracteres vai inteira, íntegra, dentro do details", async () => {
  const ementa = Array.from({ length: 250 }, (_, i) => `palavra${i % 10}`.padEnd(9, "x")).join(" ");
  assert.ok(ementa.length > 2000, "controle: a fixture é longa");

  const { html } = await detalhe(comProposicoes([proposicao({ ementa })]));

  const [item] = proposicoesNaPagina(html);
  assert.equal(item.completa, ementa);
  assert.equal(item.ementa, `${ementa.slice(0, LIMITE_DA_EMENTA).trimEnd()}…`);
});

test("detalhe: o resumo da ementa longa não termina em espaço antes do '…'", async () => {
  // O 300º caractere é um espaço: o resumo termina no 299º, não em "a …".
  const ementa = `${ementaDe(LIMITE_DA_EMENTA - 1)} ${ementaDe(20)}`;

  const { html } = await detalhe(comProposicoes([proposicao({ ementa })]));

  const [item] = proposicoesNaPagina(html);
  assert.equal(item.ementa, `${ementaDe(LIMITE_DA_EMENTA - 1)}…`);
  assert.equal(item.completa, ementa);
});

test("detalhe: o corte da ementa não parte um caractere fora do BMP (emoji)", async () => {
  const ementa = "😀".repeat(LIMITE_DA_EMENTA + 1);

  const { html } = await detalhe(comProposicoes([proposicao({ ementa })]));

  const [item] = proposicoesNaPagina(html);
  assert.equal(item.ementa, `${"😀".repeat(LIMITE_DA_EMENTA)}…`);
  assert.equal(item.completa, ementa);
});

test("detalhe: ementa longa com HTML aparece escapada no resumo e no details", async () => {
  const ementa = `<b>x</b>${ementaDe(LIMITE_DA_EMENTA)}<script>y</script>`;

  const { html } = await detalhe(comProposicoes([proposicao({ ementa })]));

  const [item] = proposicoesNaPagina(html);
  assert.ok(item.ementa.startsWith("&lt;b&gt;x&lt;/b&gt;"));
  assert.ok(item.completa.endsWith("&lt;script&gt;y&lt;/script&gt;"));
  assert.ok(!html.includes("<b>x</b>") && !html.includes("<script>y"));
});

test("detalhe sem ementa longa: nenhum details na página", async () => {
  const { html } = await detalhe(
    comProposicoes([proposicao({ ementa: null }), proposicao({ titulo: "PL 2/2026", ementa: "Curta" })]),
  );

  assert.ok(!html.includes("<details"));
});

// A tabela de votos é a parte mais longa da página (até centenas de linhas): as proposições dizem o
// que se votou e vêm antes dela, depois da contagem.
test("detalhe com votos: as proposições vêm depois da contagem e antes da tabela de votos", async () => {
  const { html } = await detalhe(comProposicoes([proposicao()]));

  const contagem = html.indexOf("<caption>Contagem por voto");
  const proposicoes = html.indexOf("<h2>Proposições</h2>");
  const votos = html.indexOf("<caption>Votos</caption>");
  assert.ok(contagem !== -1 && proposicoes !== -1 && votos !== -1, "controle: as três existem");
  assert.ok(contagem < proposicoes, "proposições depois da contagem");
  assert.ok(proposicoes < votos, "proposições antes dos votos");
});

test("detalhe sem votos: as proposições vêm depois do aviso de que não há lista nominal", async () => {
  const { html } = await detalhe(
    semVotos({
      proposicoes: [proposicao()],
      atribuicao_das_proposicoes: atribuicaoDasProposicoes(),
    }),
  );

  const aviso = html.indexOf("Esta votação não tem lista de votos nominais");
  const proposicoes = html.indexOf("<h2>Proposições</h2>");
  assert.ok(aviso !== -1 && proposicoes !== -1, "controle: as duas existem");
  assert.ok(aviso < proposicoes);
});

test("detalhe: o id da proposição não aparece (a página não tem rota para ela)", async () => {
  const { status, html } = await detalhe(comProposicoes([proposicao()]));

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.equal(proposicoesNaPagina(html).length, 1, "controle: a proposição aparece");
  assert.ok(!html.includes("4455667"));
});

test("detalhe: cita a origem das proposições com o conjunto próprio, à parte das outras duas", async () => {
  const { html } = await detalhe(comProposicoes([proposicao()]));

  assert.equal(contar(html, /aria-label="Origem dos dados"/g), 3);
  assert.ok(html.includes("Proposições das votações da Câmara (2026)"));
  assert.ok(html.includes("Votações da Câmara (2026)"));
  assert.ok(html.includes("Votos nominais da Câmara (2026)"));
});

test("detalhe: uma votação sem voto nominal e com proposições cita a votação e as proposições", async () => {
  const { html } = await detalhe(
    semVotos({
      proposicoes: [proposicao()],
      atribuicao_das_proposicoes: atribuicaoDasProposicoes(),
    }),
  );

  assert.equal(contar(html, /aria-label="Origem dos dados"/g), 2);
  assert.ok(html.includes("Proposições das votações da Câmara (2026)"));
  assert.ok(!html.includes("Votos nominais da Câmara (2026)"));
});

test("detalhe: as 213 proposições (o máximo medido) saem todas, na ordem recebida", async () => {
  const itens = Array.from({ length: 213 }, (_, i) =>
    proposicao({ id_camara: 7000000 + i, titulo: `PL ${i + 1}/2026`, ementa: `Ementa ${i + 1}` }),
  );

  const { status, html } = await detalhe(comProposicoes(itens));

  assert.equal(status, 200);
  assert.deepEqual(
    proposicoesNaPagina(html).map((item) => item.titulo),
    itens.map((item) => item.titulo),
  );
});

const proposicoesFora = {
  "proposicoes ausente": () => {
    const corpo = comProposicoes([proposicao()]);
    delete corpo.proposicoes;
    return corpo;
  },
  "proposicoes que não é lista": () => comProposicoes({ a: 1 }),
  "id_camara em texto": () => comProposicoes([proposicao({ id_camara: "4455667" })]),
  "titulo vazio": () => comProposicoes([proposicao({ titulo: "" })]),
  "titulo que não é texto": () => comProposicoes([proposicao({ titulo: 9001 })]),
  "tipo ausente": () => {
    const item = proposicao();
    delete item.tipo;
    return comProposicoes([item]);
  },
  "numero em texto": () => comProposicoes([proposicao({ numero: "9001" })]),
  "ano em texto": () => comProposicoes([proposicao({ ano: "2026" })]),
  "ano ausente (null é 'sem ano', ausente não)": () => {
    const item = proposicao();
    delete item.ano;
    return comProposicoes([item]);
  },
  "ementa vazia em vez de null (decisão 6: nunca a string vazia)": () =>
    comProposicoes([proposicao({ ementa: "" })]),
  "ementa ausente": () => {
    const item = proposicao();
    delete item.ementa;
    return comProposicoes([item]);
  },
  "origem ausente": () => {
    const item = proposicao();
    delete item.origem;
    return comProposicoes([item]);
  },
  "atribuicao_das_proposicoes ausente": () => {
    const corpo = comProposicoes([proposicao()]);
    delete corpo.atribuicao_das_proposicoes;
    return corpo;
  },
  "proposições sem a atribuição das proposições": () =>
    comProposicoes([proposicao()], { atribuicao_das_proposicoes: null }),
  "sem proposições mas com a atribuição das proposições": () =>
    nominal({ atribuicao_das_proposicoes: atribuicaoDasProposicoes() }),
  "atribuicao_das_proposicoes que não é objeto": () =>
    comProposicoes([proposicao()], { atribuicao_das_proposicoes: "x" }),
};

for (const [nome, montar] of Object.entries(proposicoesFora)) {
  test(`detalhe com proposições fora do formato é recusado inteiro: ${nome}`, async () => {
    const controle = await detalhe(comProposicoes([proposicao()]));
    assert.equal(controle.status, 200, "controle: com o formato certo a página existe");

    const { status, html } = await detalhe(montar());

    assert.equal(status, 500);
    assert.ok(!html.includes("Ementa A"));
    assert.ok(!html.includes("PL 9001/2026"));
  });
}

// --- Detalhe: totais da fonte e votação sem voto nominal -----------------------------------------

// "Não temos a lista nos dados coletados", e não "a Câmara não publicou": os votos vêm de outro
// conjunto (`votos-2026`), e uma coleta que falhou ou ainda não rodou daria a mesma lista vazia.
const SEM_LISTA = "Esta votação não tem lista de votos nominais nos dados coletados";
// Frase de fato, sem causa: o significado do zero na fonte não foi verificado (ADR 0031 e 0032).
const TOTAIS_ZERADOS = "Os totais da fonte estão zerados e não são mostrados.";

test("detalhe sem voto nominal e totais 0/0/0: diz que não há lista nos dados, sem números", async () => {
  const { status, html } = await detalhe(semVotos());

  assert.equal(status, 200);
  assert.ok(html.includes(SEM_LISTA));
  assert.match(
    html,
    new RegExp(`<p class="aviso">${SEM_LISTA}[^<]*\\. ${TOTAIS_ZERADOS.replace(/\./g, "\\.")}</p>`),
    "a frase dos totais zerados fica no mesmo aviso, depois da de 'sem lista'",
  );
  assert.ok(!html.includes("A Câmara não publicou"));
  assert.ok(!html.includes("não informou"), "o aviso não afirma uma causa que ninguém verificou");
  assert.equal(tabela(html, "Totais informados pela Câmara"), null);
  assert.equal(tabela(html, "Votos"), null);
  assert.equal(tabela(html, "Contagem por voto, contado pelo polis a partir dos votos"), null);
  assert.ok(!/<td>0<\/td>/.test(html), "0/0/0 da fonte não é contagem");
});

test("detalhe sem voto nominal e totais 10/5/1: os totais saem como informados pela Câmara", async () => {
  const { html } = await detalhe(
    semVotos({ votacao: votacaoDoDetalhe({ totais_da_fonte: totais(10, 5, 1) }) }),
  );

  const informados = tabela(html, "Totais informados pela Câmara");
  assert.ok(informados, "não achei a tabela de totais");
  assert.deepEqual(informados.linhas, [
    ["Sim", "10"],
    ["Não", "5"],
    ["Outros", "1"],
  ]);
  assert.ok(html.includes(SEM_LISTA));
  assert.ok(!html.includes(TOTAIS_ZERADOS), "os totais aparecem, então não estão zerados");
});

// Qualquer total diferente de zero basta para mostrar a tabela, e cada valor cai na sua linha: um só
// total (e em cada posição) pega a regra que olhasse só o primeiro, ou que ignorasse um deles.
for (const [nome, [sim, nao, outros]] of Object.entries({
  "só 'sim'": [4, 0, 0],
  "só 'não'": [0, 7, 0],
  "só 'outros'": [0, 0, 3],
})) {
  test(`detalhe sem voto nominal e totais com ${nome}: a tabela aparece com o valor na linha certa`, async () => {
    const { html } = await detalhe(
      semVotos({ votacao: votacaoDoDetalhe({ totais_da_fonte: totais(sim, nao, outros) }) }),
    );

    const informados = tabela(html, "Totais informados pela Câmara");
    assert.ok(informados, "não achei a tabela de totais");
    assert.deepEqual(informados.linhas, [
      ["Sim", String(sim)],
      ["Não", String(nao)],
      ["Outros", String(outros)],
    ]);
    assert.ok(!html.includes(TOTAIS_ZERADOS), "um total diferente de zero não é 'zerado'");
  });
}

test("detalhe com voto nominal e totais 0/0/0: sem a tabela de totais, com os votos", async () => {
  const { html } = await detalhe(
    nominal({ votacao: votacaoDoDetalhe({ totais_da_fonte: totais() }) }),
  );

  assert.equal(tabela(html, "Totais informados pela Câmara"), null);
  assert.ok(tabela(html, "Votos"));
  assert.ok(!html.includes(SEM_LISTA));
  assert.ok(!html.includes(TOTAIS_ZERADOS), "com votos, a contagem do polis já está na página");
});

test("detalhe com voto nominal e totais 2/1/1: a tabela de totais aparece ao lado da contagem do polis", async () => {
  const { html } = await detalhe();

  const informados = tabela(html, "Totais informados pela Câmara");
  assert.ok(informados, "não achei a tabela de totais");
  assert.deepEqual(informados.linhas, [
    ["Sim", "2"],
    ["Não", "1"],
    ["Outros", "1"],
  ]);
});

test("detalhe sem voto nominal: só a atribuição da votação", async () => {
  const { html } = await detalhe(semVotos());

  assert.equal(contar(html, /aria-label="Origem dos dados"/g), 1);
  assert.ok(html.includes("Votações da Câmara (2026)"));
  assert.ok(!html.includes("Votos nominais da Câmara (2026)"));
});

// --- Detalhe: aprovação --------------------------------------------------------------------------

test("detalhe: aprovação '0' sai como o código '0'", async () => {
  const { html } = await detalhe(semVotos({ votacao: votacaoDoDetalhe({ aprovacao: "0" }) }));

  assert.match(html, /<dt>Aprovação \(código da fonte\)<\/dt><dd>0<\/dd>/);
  assert.ok(html.includes(LEGENDA_DA_APROVACAO));
});

test("detalhe: aprovação nula e sem votos não mostra o campo nem a nota", async () => {
  const controle = await detalhe(semVotos());
  assert.ok(controle.html.includes("Aprovação (código da fonte)"), "controle: com código o campo aparece");
  assert.ok(controle.html.includes(PREFIXO_DA_NOTA), "controle: com código a nota aparece");

  const { status, html } = await detalhe(semVotos({ votacao: votacaoDoDetalhe({ aprovacao: null }) }));

  assert.equal(status, 200);
  assert.ok(!html.includes("Aprovação (código da fonte)"));
  semNota(html);
  assert.ok(!html.includes(">null<"));
});

// --- Detalhe: erros e estrutura ------------------------------------------------------------------

// A rota do Django só casa `[0-9]{1,10}-[0-9]{1,10}` com dígitos ASCII e até 20 caracteres; o front
// recusa o mesmo, sem chamar a API. "9999999999-9999999999" tem 21 caracteres (passa nas partes e
// falha no total). "٣-1" é guarda de regressão: o `[0-9]` já o recusa.
for (const invalido of [
  "abc",
  "123",
  "1-2-3",
  "-1-2",
  "1--2",
  "1-",
  "-2",
  "12345678901-1",
  "1-12345678901",
  "9999999999-9999999999",
  "1_2",
  "1.2-3",
  "-22",
  "22-",
  "٣-1",
]) {
  test(`id malformado dá 404 sem chamar a API: ${invalido}`, async () => {
    const controle = await detalhe();
    assert.equal(controle.status, 200, "controle: a página precisa existir");
    const antes = api.chamadas.length;

    const { status } = await abrir(`/camara/votacoes/${invalido}/`, { status: 200, corpo: nominal() });

    assert.equal(status, 404);
    assert.equal(api.chamadas.length, antes, "chamou a API com um id inválido");
  });
}

// O id é texto: o zero à esquerda é um registro distinto, e o de 20 caracteres é o maior que a rota
// aceita. Nenhum id que a rota aceita pode ser recusado aqui.
for (const canonico of [
  "1-2",
  "01-2",
  "2332174-59",
  "9999999999-999999999",
  "999999999-9999999999",
]) {
  test(`id que a rota aceita segue para a API: ${canonico}`, async () => {
    api.chamadas.length = 0;

    const { status } = await detalhe(nominal(), canonico);

    assert.equal(status, 200);
    assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}${canonico}/`]);
  });
}

test("id válido: a API recebe exatamente GET /internal/v1/camara/votacoes/<id>/", async () => {
  api.chamadas.length = 0;

  await detalhe();

  assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}2332174-59/`]);
});

test("API responde 404: página 404 em português", async () => {
  const controle = await detalhe();
  assert.equal(controle.status, 200, "controle: sem a rota, o 404 viria do Next e não da API");
  api.chamadas.length = 0;

  const { status, html } = await abrir("/camara/votacoes/2332174-59/", {
    status: 404,
    corpo: { erro: "não encontrado" },
  });

  assert.equal(status, 404);
  assert.match(html, /não encontrad/i);
  assert.deepEqual(api.chamadas, [`GET ${CAMINHO_DA_LISTA}2332174-59/`], "a API foi chamada uma vez");
});

test("API responde 500: erro genérico, sem o endereço da API", async () => {
  const { status, html } = await abrir("/camara/votacoes/2332174-59/", {
    status: 500,
    corpo: { erro: "boom" },
  });

  assert.equal(status, 500);
  assert.ok(!html.includes(new URL(api.url).host));
});

test("detalhe: resposta que não é JSON dá 500", async () => {
  const { status } = await abrir("/camara/votacoes/2332174-59/", {
    status: 200,
    corpo: "isto não é JSON",
  });

  assert.equal(status, 500);
});

const detalhesFora = {
  "voto de tipo errado": () => nominal({ votos: [voto(1, "Ana Souza", "ABC", 1)] }),
  "voto sem a chave (null é 'sem posição', ausente não)": () => {
    const sem = voto(1, "Ana Souza", "ABC", "Sim");
    delete sem.voto;
    return nominal({ votos: [sem] });
  },
  "partido de tipo errado": () => nominal({ votos: [voto(1, "Ana Souza", 7, "Sim")] }),
  "partido sem a chave": () => {
    const sem = voto(1, "Ana Souza", "ABC", "Sim");
    delete sem.partido;
    return nominal({ votos: [sem] });
  },
  "tem_perfil que não é booleano (texto não vira link)": () =>
    nominal({ votos: [voto(1, "Ana Souza", "ABC", "Sim", { tem_perfil: "false" })] }),
  "sem tem_perfil": () => {
    const sem = voto(1, "Ana Souza", "ABC", "Sim");
    delete sem.tem_perfil;
    return nominal({ votos: [sem] });
  },
  "nome que não é texto nem nulo": () => nominal({ votos: [voto(1, 42, "ABC", "Sim")] }),
  "id_camara que não é inteiro": () =>
    nominal({ votos: [voto(1, "Ana Souza", "ABC", "Sim", { id_camara: "1" })] }),
  "legislatura que não é inteiro": () =>
    nominal({ votos: [voto(1, "Ana Souza", "ABC", "Sim", { legislatura: "57" })] }),
  "contagem_por_voto que é objeto": () => nominal({ contagem_por_voto: { Sim: 2 } }),
  "contagem_por_voto com quantidade em texto": () =>
    nominal({ contagem_por_voto: [{ voto: "Sim", quantidade: "2" }] }),
  "contagem_por_voto sem a chave voto": () => nominal({ contagem_por_voto: [{ quantidade: 2 }] }),
  "votos que não é lista": () => nominal({ votos: { a: 1 } }),
  // Invariantes do contrato (ADR 0032): o que a API nunca manda é recusado, em vez de mostrado.
  "voto vazio em vez de null (decisão 6: nunca a string vazia)": () =>
    nominal({ votos: [voto(1, "Ana Souza", "ABC", "")] }),
  "partido vazio em vez de null": () => nominal({ votos: [voto(1, "Ana Souza", "", "Sim")] }),
  "tem_perfil verdadeiro com nome nulo (link sem texto)": () =>
    nominal({ votos: [voto(1, null, "ABC", "Sim", { tem_perfil: true })] }),
  "tem_perfil verdadeiro com nome vazio": () => nominal({ votos: [voto(1, "", "ABC", "Sim")] }),
  "tem_perfil falso com nome preenchido": () =>
    nominal({ votos: [voto(1, "Ana Souza", "ABC", "Sim", { tem_perfil: false })] }),
  "link para legislatura que a rota do deputado recusaria": () =>
    nominal({ votos: [voto(1, "Ana Souza", "ABC", "Sim", { legislatura: 0 })] }),
  "link para id da Câmara que a rota do deputado recusaria": () =>
    nominal({ votos: [voto(0, "Ana Souza", "ABC", "Sim")] }),
  "votos sem a atribuição dos votos": () => nominal({ atribuicao_dos_votos: null }),
  "sem votos mas com a atribuição dos votos": () =>
    semVotos({ atribuicao_dos_votos: atribuicaoDosVotos() }),
  "votos sem contagem por voto": () => nominal({ contagem_por_voto: [] }),
  "sem votos mas com contagem por voto": () =>
    semVotos({ contagem_por_voto: [{ voto: "Sim", quantidade: 1 }] }),
  "aprovacao de tipo errado": () => nominal({ votacao: votacaoDoDetalhe({ aprovacao: 1 }) }),
  "id_proposicao em texto": () => nominal({ votacao: votacaoDoDetalhe({ id_proposicao: "0" }) }),
  "sem atribuicao": () => {
    const corpo = nominal();
    delete corpo.atribuicao;
    return corpo;
  },
  "sem atribuicao_dos_votos (null é 'não há votos', ausente não)": () => {
    const corpo = nominal();
    delete corpo.atribuicao_dos_votos;
    return corpo;
  },
  "atribuicao_dos_votos que não é objeto": () => nominal({ atribuicao_dos_votos: "x" }),
  "totais sem 'nao'": () =>
    nominal({ votacao: votacaoDoDetalhe({ totais_da_fonte: { sim: 1, outros: 1 } }) }),
  "votacao sem descricao": () => {
    const votacao = votacaoDoDetalhe();
    delete votacao.descricao;
    return nominal({ votacao });
  },
};

for (const [nome, montar] of Object.entries(detalhesFora)) {
  test(`detalhe fora do formato é recusado inteiro: ${nome}`, async () => {
    const controle = await detalhe();
    assert.equal(controle.status, 200, "controle: com o formato certo a página existe");

    const { status, html } = await detalhe(montar());

    assert.equal(status, 500);
    assert.ok(!html.includes("Ana Souza"));
  });
}

// O contrário dos casos acima: só quem tem link precisa de um par que a rota do deputado aceite. Um
// voto sem perfil pode ter legislatura 0 ou id de 10 dígitos (`PositiveIntegerField` os admite) e a
// página tem de mostrá-lo, não dar 500 por causa de um link que nem existe.
for (const [nome, extra, idCamara] of [
  ["legislatura 0", { legislatura: 0 }, 1],
  ["id da Câmara 0", {}, 0],
  ["id da Câmara de 10 dígitos", {}, 1234567890],
]) {
  test(`detalhe: voto sem perfil e ${nome} é aceito, sem link`, async () => {
    const { status, html } = await detalhe(
      nominal({ votos: [voto(idCamara, null, "ABC", "Sim", extra)] }),
    );

    assert.equal(status, 200);
    assert.deepEqual(tabela(html, "Votos").linhas, [
      [`Deputado sem perfil (id ${idCamara})`, "ABC", "Sim"],
    ]);
    assert.ok(!html.includes('href="/deputados/'));
  });
}

test("estrutura: um h1, título com o descritor e noindex", async () => {
  for (const { status, html } of [await listaOk(), await detalhe()]) {
    assert.equal(status, 200, "controle: a 404 do Next também tem h1, título e noindex");
    assert.equal(contar(html, /<h1[ >]/g), 1);
    assert.match(html, /<title>[^<]*transparência e inteligência cívica[^<]*<\/title>/);
    assert.match(html, /<meta name="robots" content="noindex/);
  }
});
