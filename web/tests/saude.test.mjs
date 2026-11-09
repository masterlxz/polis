// Rota de saúde do front (ADR 0015). Sobe o servidor de produção que a imagem usa
// (`.next/standalone/server.js`, saída do `npm run build`) e fala com ele por HTTP.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";

const STANDALONE = fileURLToPath(new URL("../.next/standalone/", import.meta.url));
const ESPERA_MAXIMA_MS = 30_000;

let servidor;
let saida = "";
let base;

function portaLivre() {
  return new Promise((resolve, reject) => {
    const sonda = createServer();
    sonda.once("error", reject);
    sonda.listen(0, "127.0.0.1", () => {
      const { port } = sonda.address();
      sonda.close(() => resolve(port));
    });
  });
}

async function esperarNoAr(url, processo) {
  const limite = Date.now() + ESPERA_MAXIMA_MS;
  while (Date.now() < limite) {
    if (processo.exitCode !== null) {
      throw new Error(`o servidor saiu (código ${processo.exitCode}) antes de responder:\n${saida}`);
    }
    try {
      await fetch(url);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }
  throw new Error(`o servidor não respondeu em ${ESPERA_MAXIMA_MS} ms:\n${saida}`);
}

before(async () => {
  const porta = await portaLivre();
  base = `http://127.0.0.1:${porta}`;
  servidor = spawn(process.execPath, ["server.js"], {
    cwd: STANDALONE,
    env: {
      ...process.env,
      NODE_ENV: "production",
      PORT: String(porta),
      HOSTNAME: "127.0.0.1",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  });
  servidor.stdout.on("data", (pedaco) => (saida += pedaco));
  servidor.stderr.on("data", (pedaco) => (saida += pedaco));
  await esperarNoAr(`${base}/saude/`, servidor);
});

after(() => {
  servidor?.kill();
});

test("GET /saude/ responde 200 com {status: ok} em JSON", async () => {
  const resposta = await fetch(`${base}/saude/`);

  assert.equal(resposta.status, 200);
  assert.match(resposta.headers.get("content-type"), /^application\/json/);
  assert.deepEqual(await resposta.json(), { status: "ok" });
});

test("rota que não existe responde 404", async () => {
  const controle = await fetch(`${base}/saude/`);
  assert.equal(controle.status, 200, "controle: /saude/ precisa existir");

  const resposta = await fetch(`${base}/nao-existe/`);

  assert.equal(resposta.status, 404);
});

test("POST em /saude/ é recusado com 405", async () => {
  const controle = await fetch(`${base}/saude/`);
  assert.equal(controle.status, 200, "controle: /saude/ precisa existir");

  const resposta = await fetch(`${base}/saude/`, { method: "POST" });

  assert.equal(resposta.status, 405);
});
