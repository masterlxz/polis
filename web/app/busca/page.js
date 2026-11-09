import { buscarPessoas, prepararConsulta } from "../../lib/api.js";

// Sem cache: quem a fonte retirar (lápide, ADR 0005) precisa sumir na hora.
export const dynamic = "force-dynamic";

// Título fixo: não reflete o que o usuário digitou.
export const metadata = {
  title: "Buscar pessoas | polis: transparência e inteligência cívica",
};

function Detalhe({ resultado }) {
  const partes = [resultado.uf, resultado.partido].filter(Boolean);
  return <span className="detalhe">{[...partes, `ciclo ${resultado.ciclo}`].join(" · ")}</span>;
}

function Resultados({ resultados }) {
  if (resultados.length === 0) {
    return (
      <p role="status">Nenhuma pessoa encontrada. Digite pelo menos 2 letras ou números.</p>
    );
  }
  const contagem = `${resultados.length} ${resultados.length === 1 ? "resultado" : "resultados"}`;
  return (
    <section aria-labelledby="resultados">
      <h2 id="resultados">{contagem}</h2>
      <p className="nota">
        Quando há poucos resultados exatos, a lista inclui nomes parecidos com o digitado.
      </p>
      <ol className="resultados">
        {resultados.map((resultado) => (
          <li key={resultado.id}>
            <a href={`/pessoas/${resultado.id}/`}>{resultado.nome}</a>
            <Detalhe resultado={resultado} />
          </li>
        ))}
      </ol>
    </section>
  );
}

export default async function Busca({ searchParams }) {
  const { q } = await searchParams;
  const consulta = prepararConsulta(q);
  const resultados = consulta ? await buscarPessoas(consulta) : null;

  return (
    <>
      <h1>Buscar pessoas</h1>
      <form action="/busca/" method="get" role="search" className="busca">
        <label htmlFor="q">Nome de urna</label>
        <input id="q" name="q" type="search" maxLength={100} defaultValue={consulta} />
        <button type="submit">Buscar</button>
      </form>
      {resultados && <Resultados resultados={resultados} />}
    </>
  );
}
