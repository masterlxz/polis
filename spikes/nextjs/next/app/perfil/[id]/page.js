import { notFound } from "next/navigation";
import Origem from "../../origem";

export const dynamic = "force-dynamic";

const API = process.env.API_URL || "http://django:8000";

export default async function Perfil({ params }) {
  const { id } = await params;
  const r = await fetch(`${API}/api/perfil/${encodeURIComponent(id)}/`, { cache: "no-store" });
  if (r.status === 404) notFound();
  const p = await r.json();
  return (
    <>
      <h1>{p.nome_publico}</h1>
      <dl>
        <dt>Cargo</dt>
        <dd>{p.cargo}</dd>
        <dt>UF</dt>
        <dd>{p.uf}</dd>
        <dt>Partido</dt>
        <dd>{p.partido}</dd>
      </dl>
      <Origem p={p} />
    </>
  );
}
