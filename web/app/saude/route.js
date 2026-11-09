// Saúde do processo, para o healthcheck do Compose. Não toca na API nem no banco.
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ status: "ok" });
}
