import { buscarVotacoesDaCamara, prepararPagina } from "../../../lib/api.js";
import { tituloDaVotacao } from "../../../lib/camara.js";
import Atribuicao from "../../pessoas/[id]/Atribuicao.js";

// Sem cache: o que a fonte corrigir precisa aparecer na hora.
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Votações da Câmara | polis: transparência e inteligência cívica",
};

const CAMINHO = "/camara/votacoes/";

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

// Só 1,9% das votações têm voto nominal (ADR 0031): as outras só têm os totais da fonte. A lista
// marca qual é qual; o id da proposição não aparece (0 é sentinela de "sem proposição").
export default async function VotacoesDaCamara({ searchParams }) {
  const { pagina: paginaBruta } = await searchParams;
  const { votacoes, pagina, total_paginas: totalPaginas, atribuicao } =
    await buscarVotacoesDaCamara(prepararPagina(paginaBruta));

  return (
    <>
      <h1>Votações da Câmara</h1>
      {votacoes.length === 0 ? (
        <Vazia totalPaginas={totalPaginas} />
      ) : (
        <ol className="resultados">
          {votacoes.map((votacao) => (
            <li key={votacao.id}>
              <a href={`${CAMINHO}${votacao.id}/`}>{tituloDaVotacao(votacao)}</a>
              <span className="detalhe">
                {votacao.tem_votos_nominais ? "Sem votos nominais" : "Com votos nominais"}
              </span>
              {votacao.descricao && <p className="ementa">{votacao.descricao}</p>}
            </li>
          ))}
        </ol>
      )}
      <Navegacao pagina={pagina} totalPaginas={totalPaginas} />
      {atribuicao && <Atribuicao atribuicao={atribuicao} />}
    </>
  );
}
