// Ponta a ponta das tramitações da Câmara (ADR 0035), no CI (job `ponta-a-ponta`): o Django REAL com
// banco REAL (semeado por `.github/ci/semear_camara.py`) e o servidor de produção do Next.js REAL.
// Os testes de `web/tests/` usam uma API falsa e os do Django não veem a página; este arquivo prova
// que o formato que a API manda é o que a página aceita. Não prova layout nem CSS (isso exige olhar
// a tela), nem o comportamento com os dados reais do dono.
//
// Roda com `node --test e2e/`, a partir de `web/`, com `API_BASE` e `FRONT_BASE` no ambiente.
import assert from "node:assert/strict";
import { test } from "node:test";

import { NOTA_DAS_TRAMITACOES, SEM_TRAMITACAO } from "../lib/camara.js";

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8000";
const FRONT_BASE = process.env.FRONT_BASE ?? "http://127.0.0.1:3000";

async function pedir(base, caminho) {
  const resposta = await fetch(`${base}${caminho}`, { redirect: "manual" });
  return { status: resposta.status, corpo: await resposta.text() };
}

// O texto que a pessoa lê: sem comentários nem tags, com as entidades que o React escreve.
function texto(html) {
  return html
    .replace(/<!--.*?-->/gs, "")
    .replace(/<script.*?<\/script>/gs, "")
    .replace(/<style.*?<\/style>/gs, "")
    .replace(/<[^>]*>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

test("API real: a proposição 14666 vem com as 3 tramitações em ordem e hora de Brasília", async () => {
  const { status, corpo } = await pedir(API_BASE, "/internal/v1/camara/proposicoes/14666/");
  assert.equal(status, 200);
  const json = JSON.parse(corpo);
  assert.deepEqual(
    json.tramitacoes.map((t) => [t.sequencia, t.data_hora, t.descricao]),
    [
      [152, "2026-05-07T16:58:00-03:00", "Apresentação de Requerimento"],
      [null, "2026-05-07T16:58:00-03:00", "Registro sem sequência na fonte"],
      [153, "2026-05-08T09:00:00-03:00", "Despacho <b>negrito</b> da Mesa"],
    ],
  );
});

test("página: a proposição 14666 mostra título, ementa, hora em Brasília e a ordem da API", async () => {
  const { status, corpo } = await pedir(FRONT_BASE, "/camara/proposicoes/14666/");
  assert.equal(status, 200);
  const lido = texto(corpo);
  assert.ok(lido.includes("PL 11/2003"), "título");
  assert.ok(lido.includes("Proíbe a veiculação de peças publicitárias."), "ementa");
  assert.ok(lido.includes(NOTA_DAS_TRAMITACOES), "nota das tramitações");
  assert.ok(lido.includes("07/05/2026 às 16:58"), "hora em Brasília");
  assert.ok(lido.includes("08/05/2026 às 09:00"), "segunda hora em Brasília");
  const posicoes = [
    "Apresentação de Requerimento",
    "Registro sem sequência na fonte",
    "Despacho <b>negrito</b> da Mesa",
  ].map((descricao) => lido.indexOf(descricao));
  assert.ok(posicoes.every((p) => p >= 0), `descrições na página: ${posicoes}`);
  assert.deepEqual(posicoes, [...posicoes].sort((a, b) => a - b), "ordem das tramitações");
  assert.ok(!lido.includes(SEM_TRAMITACAO), "não pode dizer que não há tramitação");
});

test("página: a descrição com HTML sai como texto escapado, nunca como tag", async () => {
  const { corpo } = await pedir(FRONT_BASE, "/camara/proposicoes/14666/");
  assert.ok(corpo.includes("&lt;b&gt;negrito&lt;/b&gt;"), "o texto escapado está no HTML");
  assert.ok(!corpo.includes("<b>negrito"), "nenhuma tag <b> viva vinda da fonte");
});

test("página: a proposição 14667, sem tramitação, diz isso", async () => {
  const { status, corpo } = await pedir(FRONT_BASE, "/camara/proposicoes/14667/");
  assert.equal(status, 200);
  const lido = texto(corpo);
  assert.ok(lido.includes("PL 12/2003"), "título");
  assert.ok(lido.includes(SEM_TRAMITACAO), "frase de sem tramitação");
});

test("a proposição 99999 tem tramitação mas o polis não a conhece: 404 na API e na página", async () => {
  assert.equal((await pedir(API_BASE, "/internal/v1/camara/proposicoes/99999/")).status, 404);
  assert.equal((await pedir(FRONT_BASE, "/camara/proposicoes/99999/")).status, 404);
});

test("página: id que não é número é 404", async () => {
  assert.equal((await pedir(FRONT_BASE, "/camara/proposicoes/abc/")).status, 404);
});

test("página da votação: link 'Ver tramitação (3)' só para a proposição com tramitação", async () => {
  const { status, corpo } = await pedir(FRONT_BASE, "/camara/votacoes/9000001-1/");
  assert.equal(status, 200);
  const lido = texto(corpo);
  assert.ok(lido.includes("PL 11/2003") && lido.includes("PL 12/2003"), "as duas proposições");
  assert.ok(lido.includes("Ver tramitação (3)"), "texto do link");
  assert.ok(corpo.includes('href="/camara/proposicoes/14666/"'), "o link aponta para a 14666");
  assert.equal(lido.split("Ver tramitação").length - 1, 1, "só um link");
  assert.ok(!corpo.includes('href="/camara/proposicoes/14667/"'), "sem link para a 14667");
});
