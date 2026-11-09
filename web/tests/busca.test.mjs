// Página de busca (`/busca/?q=...`, ADR 0015 e ADR 0016) e a entrada do site (`/` e o link
// "Buscar" no cabeçalho), contra o servidor de produção e uma API falsa. Dados todos
// sintéticos. O que mais importa: o que o usuário digita vai para a API codificado e cortado,
// volta escapado na tela, o `id` de cada resultado só vira link se tiver o formato esperado, e
// a falha da API não vaza o endereço dela.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarApiFalsa, iniciarNext } from "./helpers.mjs";

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

function resultado({ id = "2026-123", nome = "MARIA SILVA", uf = "SP", partido = "XYZ" } = {}) {
  return { id, nome, ciclo: 2026, uf, partido };
}

function lista(...resultados) {
  return { status: 200, corpo: { resultados } };
}

// O SSR do React separa textos vizinhos com `<!-- -->`; tirar isso deixa a conferência do texto
// visível independente de como o componente foi escrito.
function limpo(html) {
  return html.replaceAll("<!-- -->", "");
}

async function buscar(consulta, resposta = lista(resultado()), { base = front.base } = {}) {
  api.resposta = () => resposta;
  api.chamadas.length = 0;
  const parametro = consulta === undefined ? "" : `?q=${encodeURIComponent(consulta)}`;
  const retorno = await fetch(`${base}/busca/${parametro}`);
  return { status: retorno.status, html: limpo(await retorno.text()), chamadas: [...api.chamadas] };
}

// O `q` que a API recebeu na primeira chamada, já decodificado.
function qRecebido(chamadas) {
  assert.ok(chamadas.length >= 1, "a API não foi chamada");
  const [metodo, caminho] = chamadas[0].split(" ");
  assert.equal(metodo, "GET");
  const url = new URL(caminho, "http://api.teste");
  assert.equal(url.pathname, "/internal/v1/busca/");
  return url.searchParams.get("q");
}

// O texto visível da linha de detalhe do primeiro resultado (o HTML inteiro tem `null` legítimo
// nos scripts de hidratação do Next, então não dá para procurar "null" nele).
function detalhe(html) {
  const [, texto] = html.match(/<span class="detalhe">([^<]*)<\/span>/) ?? [];
  assert.notEqual(texto, undefined, "não há linha de detalhe na página");
  return texto;
}

function tagInput(html) {
  const [tag] = html.match(/<input[^>]*>/) ?? [];
  assert.ok(tag, "não há campo de busca na página");
  return tag;
}

test("sem q: título, formulário com rótulo e nenhuma chamada à API", async () => {
  const { status, html, chamadas } = await buscar(undefined);

  assert.equal(status, 200);
  assert.match(html, /<h1[^>]*>Buscar pessoas<\/h1>/);
  assert.match(html, /<form[^>]*role="search"/);
  assert.match(html, /<label[^>]*for="q"/);
  const campo = tagInput(html);
  assert.match(campo, /id="q"/);
  assert.match(campo, /name="q"/);
  assert.match(campo, /type="search"/);
  assert.deepEqual(chamadas, []);
});

test("com resultados: nomes como link para o perfil e o q certo na API", async () => {
  const { status, html, chamadas } = await buscar(
    "maria silva",
    lista(
      resultado({ id: "2026-123", nome: "MARIA SILVA" }),
      resultado({ id: "2026-456", nome: "MARIA DA SILVA" }),
    ),
  );

  assert.equal(status, 200);
  assert.match(html, /<a[^>]*href="\/pessoas\/2026-123\/"[^>]*>MARIA SILVA<\/a>/);
  assert.match(html, /<a[^>]*href="\/pessoas\/2026-456\/"[^>]*>MARIA DA SILVA<\/a>/);
  assert.deepEqual(chamadas, ["GET /internal/v1/busca/?q=maria+silva"]);
});

test("UF, partido e ciclo aparecem; UF ou partido nulos somem, sem escrever null", async () => {
  const completo = await buscar("maria", lista(resultado({ uf: "SP", partido: "XYZ" })));
  assert.equal(completo.status, 200);
  assert.equal(detalhe(completo.html), "SP · XYZ · ciclo 2026");

  const semUf = await buscar("maria", lista(resultado({ uf: null, partido: "XYZ" })));
  assert.equal(detalhe(semUf.html), "XYZ · ciclo 2026");

  const semNada = await buscar("maria", lista(resultado({ uf: null, partido: null })));
  assert.equal(semNada.status, 200);
  assert.equal(detalhe(semNada.html), "ciclo 2026");
});

test("acento e símbolos vão codificados e chegam inteiros à API", async () => {
  const { status, chamadas } = await buscar("joão & cia");

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.equal(qRecebido(chamadas), "joão & cia");
});

test("lista vazia: mensagem em português e o texto digitado continua no campo", async () => {
  const { status, html } = await buscar("zzzz", lista());

  assert.equal(status, 200);
  assert.ok(html.includes("Nenhuma pessoa encontrada. Digite pelo menos 2 letras ou números."));
  assert.match(tagInput(html), /value="zzzz"/);
});

test("HTML no q ou no nome aparece escapado, sem tag ativa", async () => {
  const noQ = await buscar("<script>alert(1)</script>", lista());
  assert.equal(noQ.status, 200, "controle: a página precisa existir");
  assert.ok(!noQ.html.includes("<script>alert(1)</script>"));
  assert.ok(noQ.html.includes("&lt;script&gt;alert(1)&lt;/script&gt;"));

  const noNome = await buscar("maria", lista(resultado({ nome: "<b>x</b>" })));
  assert.equal(noNome.status, 200);
  assert.ok(!noNome.html.includes("<b>x</b>"));
  assert.ok(noNome.html.includes("&lt;b&gt;x&lt;/b&gt;"));
});

test("q com 500 caracteres: a API recebe no máximo 100", async () => {
  const { status, chamadas } = await buscar("a".repeat(500));

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.equal(qRecebido(chamadas).length, 100);
});

test("q repetido: vale o primeiro", async () => {
  api.resposta = () => lista(resultado());
  api.chamadas.length = 0;

  const retorno = await fetch(`${front.base}/busca/?q=ana&q=maria`);

  assert.equal(retorno.status, 200, "controle: a página precisa existir");
  assert.equal(qRecebido([...api.chamadas]), "ana");
});

test("q vazio ou só espaços: só o formulário, sem chamar a API", async () => {
  const controle = await buscar("maria");
  assert.equal(controle.status, 200, "controle: a API precisa estar alcançável");
  assert.equal(controle.chamadas.length, 1, "controle: com q a API é chamada");

  for (const consulta of ["", "   "]) {
    const { status, html, chamadas } = await buscar(consulta);
    assert.equal(status, 200);
    assert.match(html, /<h1[^>]*>Buscar pessoas<\/h1>/);
    assert.deepEqual(chamadas, [], `chamou a API com q=${JSON.stringify(consulta)}`);
  }
});

test("q de 1 caractere ainda chama a API e, sem resultado, mostra a mesma mensagem", async () => {
  const { status, html, chamadas } = await buscar("a", lista());

  assert.equal(status, 200);
  assert.equal(qRecebido(chamadas), "a");
  assert.ok(html.includes("Nenhuma pessoa encontrada. Digite pelo menos 2 letras ou números."));
});

test("contagem no singular e no plural, e a nota dos nomes parecidos só com resultados", async () => {
  const um = await buscar("maria", lista(resultado()));
  assert.equal(um.status, 200);
  assert.match(um.html, /\b1 resultado\b(?!s)/);

  const dois = await buscar("maria", lista(resultado(), resultado({ id: "2026-456" })));
  assert.match(dois.html, /\b2 resultados\b/);
  assert.match(dois.html, /nomes parecidos com o digitado/);

  const nenhum = await buscar("maria", lista());
  assert.equal(nenhum.status, 200);
  assert.ok(!/nomes parecidos com o digitado/.test(nenhum.html));
});

test("API responde 500: erro 500 genérico, sem o endereço da API", async () => {
  const { status, html, chamadas } = await buscar("maria", {
    status: 500,
    corpo: { erro: "boom" },
  });

  assert.equal(status, 500);
  assert.equal(chamadas.length, 1, "a API não foi chamada");
  assert.ok(!html.includes(api.url));
  assert.ok(!html.includes(new URL(api.url).host));
});

test("API fora do ar: erro 500 sem o endereço da API", async () => {
  const porta = api.url.split(":").pop();
  const parado = await iniciarNext({ apiUrl: "http://127.0.0.1:9" });
  try {
    const controle = await fetch(`${parado.base}/busca/`);
    assert.equal(controle.status, 200, "controle: sem q a página não depende da API");

    const resposta = await fetch(`${parado.base}/busca/?q=maria`);
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

    const resposta = await fetch(`${lento.base}/busca/?q=maria`);

    assert.equal(resposta.status, 500);
    assert.ok(Date.now() - antes < 10_000, "não respeitou o tempo limite");
  } finally {
    lento.parar();
  }
});

for (const [descricao, corpo] of [
  ["id com esquema perigoso", { resultados: [resultado({ id: "javascript:alert(1)" })] }],
  ["id fora do formato", { resultados: [resultado({ id: "2026-abc" })] }],
  ["item sem nome", { resultados: [{ id: "2026-123", ciclo: 2026, uf: "SP", partido: "XYZ" }] }],
  ["corpo sem a lista", { outra: [] }],
]) {
  test(`API devolve formato inválido (${descricao}): erro 500 e nenhum link com o valor`, async () => {
    const controle = await buscar("maria");
    assert.equal(controle.status, 200, "controle: o formato válido precisa funcionar");

    const { status, html } = await buscar("maria", { status: 200, corpo });

    assert.equal(status, 500);
    assert.ok(!html.includes("javascript:alert(1)"));
    assert.ok(!html.includes("2026-abc"));
  });
}

test("a raiz redireciona (307) para /busca/", async () => {
  const controle = await buscar(undefined);
  assert.equal(controle.status, 200, "controle: /busca/ precisa existir");

  const resposta = await fetch(`${front.base}/`, { redirect: "manual" });

  assert.equal(resposta.status, 307);
  assert.equal(new URL(resposta.headers.get("location"), front.base).pathname, "/busca/");
});

test("o cabeçalho de toda página tem o link Buscar para /busca/", async () => {
  const perfilMinimo = { pessoa: { ciclo: 2026, id_tse: 1, nome: "FULANO" }, candidaturas: [] };
  api.resposta = () => ({ status: 200, corpo: perfilMinimo });
  const naPessoa = await fetch(`${front.base}/pessoas/2026-1/`);
  const htmlPessoa = limpo(await naPessoa.text());
  const naBusca = await buscar(undefined);

  assert.equal(naPessoa.status, 200, "controle: o perfil precisa existir");
  for (const html of [htmlPessoa, naBusca.html]) {
    assert.match(html, /<nav[^>]*aria-label="Principal"/);
    assert.match(html, /<nav[^>]*>.*<a[^>]*href="\/busca\/"[^>]*>Buscar<\/a>.*<\/nav>/s);
  }
});

test("estrutura: idioma pt-BR, um h1, título com o descritor e noindex", async () => {
  const { status, html } = await buscar("maria");

  assert.equal(status, 200, "controle: a página precisa existir");
  assert.match(html, /<html[^>]*lang="pt-BR"/);
  assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1);
  assert.match(html, /<title>[^<]*transparência e inteligência cívica[^<]*<\/title>/);
  assert.match(html, /<meta name="robots" content="noindex/);
});
