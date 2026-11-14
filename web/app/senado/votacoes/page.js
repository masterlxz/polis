import { buscarVotacoesDoSenado, prepararPagina } from "../../../lib/api.js";
import { dataBr } from "../../../lib/formatar.js";
import { resultadoParaExibir } from "../../../lib/siglas.js";
import Atribuicao from "../../pessoas/[id]/Atribuicao.js";

// Sem cache: o que a fonte corrigir precisa aparecer na hora.
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Votações do Senado | polis: transparência e inteligência cívica",
};

const CAMINHO = "/senado/votacoes/";

function Navegacao({ pagina, totalPaginas }) {
  const temAnterior = pagina > 1 && pagina <= totalPaginas;
  const temProxima = pagina < totalPaginas;
  if (!temAnterior && !temProxima) return null;
  return (
    <nav aria-label="Páginas" className="paginas">
      {temAnterior && <a href={`${CAMINHO}?pagina=${pagina - 1}`}>Anterior</a>}
      <span>{`Página ${pagina} de ${totalPaginas}`}</span>
      {temProxima && <a href={`${CAMINHO}?pagina=${pagina + 1}`}>Próxima</a>}
    </nav>
  );
}

function Vazia({ totalPaginas }) {
  if (totalPaginas === 0) return <p role="status">Nenhuma votação coletada ainda.</p>;
  return (
    <p role="status">
      {"Nenhuma votação nesta página. "}
      <a href={CAMINHO}>Voltar para a primeira página</a>
    </p>
  );
}

export default async function VotacoesDoSenado({ searchParams }) {
  const { pagina: paginaBruta } = await searchParams;
  const { votacoes, pagina, total_paginas: totalPaginas, atribuicao } =
    await buscarVotacoesDoSenado(prepararPagina(paginaBruta));

  return (
    <>
      <h1>Votações do Senado</h1>
      {votacoes.length === 0 ? (
        <Vazia totalPaginas={totalPaginas} />
      ) : (
        <ol className="resultados">
          {votacoes.map((votacao) => (
            <li key={votacao.codigo}>
              <a href={`${CAMINHO}${votacao.codigo}/`}>{votacao.identificacao}</a>
              <span className="detalhe">
                {[dataBr(votacao.data), resultadoParaExibir(votacao.resultado).curto]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              {votacao.secreta && <span className="detalhe">Votação secreta</span>}
              {votacao.ementa && <p className="ementa">{votacao.ementa}</p>}
            </li>
          ))}
        </ol>
      )}
      <Navegacao pagina={pagina} totalPaginas={totalPaginas} />
      {atribuicao && <Atribuicao atribuicao={atribuicao} />}
    </>
  );
}
