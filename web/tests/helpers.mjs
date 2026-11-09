// Ferramentas dos testes do front: sobe o servidor de produção do Next.js
// (`.next/standalone/server.js`, saída do `npm run build`) e uma API falsa que imita a API
// interna do Django, para os testes dizerem o que a API devolve e o que o front pediu a ela.
import { spawn } from "node:child_process";
import { createServer as criarServidorHttp } from "node:http";
import { createServer as criarServidorTcp } from "node:net";
import { fileURLToPath } from "node:url";

const STANDALONE = fileURLToPath(new URL("../.next/standalone/", import.meta.url));
const ESPERA_MAXIMA_MS = 30_000;

export function portaLivre() {
  return new Promise((resolve, reject) => {
    const sonda = criarServidorTcp();
    sonda.once("error", reject);
    sonda.listen(0, "127.0.0.1", () => {
      const { port } = sonda.address();
      sonda.close(() => resolve(port));
    });
  });
}

async function esperarNoAr(url, processo, saida) {
  const limite = Date.now() + ESPERA_MAXIMA_MS;
  while (Date.now() < limite) {
    if (processo.exitCode !== null) {
      throw new Error(
        `o servidor saiu (código ${processo.exitCode}) antes de responder:\n${saida()}`,
      );
    }
    try {
      await fetch(url);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }
  throw new Error(`o servidor não respondeu em ${ESPERA_MAXIMA_MS} ms:\n${saida()}`);
}

// `apiUrl` aponta para onde o front acha que está a API; por padrão, uma porta fechada.
export async function iniciarNext({ apiUrl = "http://127.0.0.1:9", env = {} } = {}) {
  const porta = await portaLivre();
  const base = `http://127.0.0.1:${porta}`;
  let texto = "";
  const saida = () => texto;
  const processo = spawn(process.execPath, ["server.js"], {
    cwd: STANDALONE,
    env: {
      ...process.env,
      NODE_ENV: "production",
      PORT: String(porta),
      HOSTNAME: "127.0.0.1",
      NEXT_TELEMETRY_DISABLED: "1",
      API_URL: apiUrl,
      ...env,
    },
  });
  processo.stdout.on("data", (pedaco) => (texto += pedaco));
  processo.stderr.on("data", (pedaco) => (texto += pedaco));
  await esperarNoAr(`${base}/saude/`, processo, saida);
  return { base, saida, parar: () => processo.kill() };
}

// API falsa. `chamadas` registra "MÉTODO caminho" de cada pedido recebido. Troque `resposta`
// em cada teste: devolve `{status, corpo}` (corpo objeto vira JSON) ou `{travar: true}`, que
// nunca responde (para testar o tempo limite).
export async function iniciarApiFalsa() {
  const api = {
    chamadas: [],
    resposta: () => ({ status: 200, corpo: {} }),
  };
  const servidor = criarServidorHttp(async (req, res) => {
    api.chamadas.push(`${req.method} ${req.url}`);
    const { status, corpo, travar } = await api.resposta(req);
    if (travar) return;
    res.writeHead(status, { "content-type": "application/json" });
    res.end(typeof corpo === "string" ? corpo : JSON.stringify(corpo));
  });
  await new Promise((resolve) => servidor.listen(0, "127.0.0.1", resolve));
  api.url = `http://127.0.0.1:${servidor.address().port}`;
  api.parar = () => {
    servidor.closeAllConnections();
    servidor.close();
  };
  return api;
}
