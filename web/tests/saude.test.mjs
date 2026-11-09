// Rota de saúde do front (ADR 0015), contra o servidor de produção.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";

import { iniciarNext } from "./helpers.mjs";

let front;

before(async () => {
  front = await iniciarNext();
});

after(() => {
  front?.parar();
});

test("GET /saude/ responde 200 com {status: ok} em JSON", async () => {
  const resposta = await fetch(`${front.base}/saude/`);

  assert.equal(resposta.status, 200);
  assert.match(resposta.headers.get("content-type"), /^application\/json/);
  assert.deepEqual(await resposta.json(), { status: "ok" });
});

test("rota que não existe responde 404", async () => {
  const controle = await fetch(`${front.base}/saude/`);
  assert.equal(controle.status, 200, "controle: /saude/ precisa existir");

  const resposta = await fetch(`${front.base}/nao-existe/`);

  assert.equal(resposta.status, 404);
});

test("POST em /saude/ é recusado com 405", async () => {
  const controle = await fetch(`${front.base}/saude/`);
  assert.equal(controle.status, 200, "controle: /saude/ precisa existir");

  const resposta = await fetch(`${front.base}/saude/`, { method: "POST" });

  assert.equal(resposta.status, 405);
});
