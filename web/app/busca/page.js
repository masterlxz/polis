import {
  UFS,
  buscarPessoas,
  prepararConsulta,
  prepararPartido,
  prepararUf,
} from "../../lib/api.js";

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

function Parecido({ resultado }) {
  return resultado.aproximado ? <span className="detalhe">nome parecido</span> : null;
}

function Resultados({ resultados, comFiltro }) {
  if (resultados.length === 0) {
    return comFiltro ? (
      <p role="status">
        Nenhuma pessoa encontrada com esses filtros. Tente tirar a UF ou o partido.
      </p>
    ) : (
      <p role="status">Nenhuma pessoa encontrada. Digite pelo menos 2 letras ou números.</p>
    );
  }
  const contagem = `${resultados.length} ${resultados.length === 1 ? "resultado" : "resultados"}`;
  return (
    <section aria-labelledby="resultados">
      <h2 id="resultados">{contagem}</h2>
      {resultados.some((resultado) => resultado.aproximado) && (
        <p className="nota">
          Quando há poucos resultados exatos, a lista inclui nomes parecidos com o digitado.
        </p>
      )}
      <ol className="resultados">
        {resultados.map((resultado) => (
          <li key={resultado.id}>
            <a href={`/pessoas/${resultado.id}/`}>{resultado.nome}</a>
            <Detalhe resultado={resultado} />
            <Parecido resultado={resultado} />
          </li>
        ))}
      </ol>
    </section>
  );
}

export default async function Busca({ searchParams }) {
  const { q, uf: ufBruta, partido: partidoBruto } = await searchParams;
  const consulta = prepararConsulta(q);
  const uf = prepararUf(ufBruta);
  const partido = prepararPartido(partidoBruto);
  const comFiltro = Boolean(uf || partido);
  const resultados = consulta ? await buscarPessoas(consulta, { uf, partido }) : null;

  return (
    <>
      <h1>Buscar pessoas</h1>
      <form action="/busca/" method="get" role="search" className="busca">
        <div className="campo campo-nome">
          <label htmlFor="q">Nome de urna</label>
          <input id="q" name="q" type="search" maxLength={100} defaultValue={consulta} />
        </div>
        <div className="campo">
          <label htmlFor="uf">UF</label>
          <select id="uf" name="uf" defaultValue={uf}>
            <option value="">Todas as UFs</option>
            {UFS.map((sigla) => (
              <option key={sigla} value={sigla}>
                {sigla}
              </option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="partido">Partido (sigla)</label>
          <input
            id="partido"
            name="partido"
            type="text"
            maxLength={20}
            defaultValue={partido}
            aria-describedby="dica-partido"
          />
          <span id="dica-partido" className="dica">
            Ex.: PT, PL
          </span>
        </div>
        <button type="submit">Buscar</button>
      </form>
      {!consulta && comFiltro && (
        <p role="status">Digite um nome para buscar. UF e partido só refinam a busca.</p>
      )}
      {resultados && <Resultados resultados={resultados} comFiltro={comFiltro} />}
    </>
  );
}
