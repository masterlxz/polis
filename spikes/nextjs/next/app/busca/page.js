import Origem from "../origem";

export const dynamic = "force-dynamic";

const API = process.env.API_URL || "http://django:8000";

export default async function Busca({ searchParams }) {
  const { q = "" } = await searchParams;
  const r = await fetch(`${API}/api/busca/?q=${encodeURIComponent(q)}`, { cache: "no-store" });
  const { itens } = await r.json();
  return (
    <>
      <form method="get">
        <input name="q" defaultValue={q} />
        <button>Buscar</button>
      </form>
      <ul>
        {itens.map((p) => (
          <li key={p.id}>
            <a href={`/perfil/${p.id}/`}>{p.nome_publico}</a> — {p.cargo} ({p.uf}, {p.partido}) <Origem p={p} />
          </li>
        ))}
      </ul>
    </>
  );
}
