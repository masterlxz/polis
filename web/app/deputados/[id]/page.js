import { notFound } from "next/navigation";

import { buscarDeputado, buscarVotosDoDeputado, prepararPagina } from "../../../lib/api.js";
import { dataBr } from "../../../lib/formatar.js";
import Nota from "../../camara/Nota.js";
import Atribuicao from "../../pessoas/[id]/Atribuicao.js";

// Sem cache: quem a fonte retirar (lápide, ADR 0005) precisa sumir na hora.
export const dynamic = "force-dynamic";

const DESCRITOR = "polis: transparência e inteligência cívica";

export async function generateMetadata({ params }) {
  const { id } = await params;
  const perfil = await buscarDeputado(id);
  const titulo = perfil ? perfil.deputado.nome : "Deputado não encontrado";
  return { title: `${titulo} | ${DESCRITOR}` };
}

// Cada rótulo some quando o valor é nulo ou vazio: nada de "—" nem "null" na tela.
function Campo({ rotulo, children }) {
  if (children === null || children === undefined || children === "") return null;
  return (
    <div>
      <dt>{rotulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Navegacao({ caminho, pagina, totalPaginas }) {
  const temAnterior = pagina > 1 && pagina <= totalPaginas;
  const temProxima = pagina < totalPaginas;
  if (!temAnterior && !temProxima) return null;
  return (
    <nav aria-label="Páginas de votos" className="paginas">
      {temAnterior && <a href={`${caminho}?pagina=${pagina - 1}`}>Anterior</a>}
      <span>{`Página ${pagina} de ${totalPaginas}`}</span>
      {temProxima && <a href={`${caminho}?pagina=${pagina + 1}`}>Próxima</a>}
    </nav>
  );
}

function SemVotos({ caminho, totalPaginas }) {
  if (totalPaginas === 0) return <p role="status">Nenhum voto coletado ainda.</p>;
  return (
    <p role="status">
      {"Nenhum voto nesta página. "}
      <a href={caminho}>Voltar para a primeira página</a>
    </p>
  );
}

// `voto` nulo é a ausência de posição na fonte: a tela diz isso em vez de deixar a célula vazia.
// `aprovacao` e as siglas de voto saem cruas, com a legenda da documentação da Câmara (ADR 0032,
// emenda 2). Partido é o do momento do voto, não o do perfil.
function Votos({ caminho, historico }) {
  const {
    votos,
    pagina,
    total_paginas: totalPaginas,
    atribuicao_das_votacoes: atribuicaoDasVotacoes,
    atribuicao_dos_votos: atribuicaoDosVotos,
  } = historico;
  return (
    <section aria-labelledby="deputado-votos" className="candidatura">
      <h2 id="deputado-votos">Votos</h2>
      {votos.length === 0 ? (
        <SemVotos caminho={caminho} totalPaginas={totalPaginas} />
      ) : (
        <table className="tabela">
          <caption>Votos registrados na Câmara dos Deputados</caption>
          <thead>
            <tr>
              <th scope="col">Data</th>
              <th scope="col">Órgão</th>
              <th scope="col">Descrição</th>
              <th scope="col">Aprovação (código da fonte)</th>
              <th scope="col">Partido (à época)</th>
              <th scope="col">Voto</th>
            </tr>
          </thead>
          <tbody>
            {votos.map((item) => (
              <tr key={item.id}>
                <td>{dataBr(item.data) ?? item.data}</td>
                <td>{item.orgao}</td>
                <td>{item.descricao}</td>
                <td>{item.aprovacao}</td>
                <td>{item.partido}</td>
                <td>{item.voto ?? "Sem posição registrada"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {votos.length > 0 && <Nota aprovacao siglas />}
      <Navegacao caminho={caminho} pagina={pagina} totalPaginas={totalPaginas} />
      {atribuicaoDasVotacoes && <Atribuicao atribuicao={atribuicaoDasVotacoes} />}
      {atribuicaoDosVotos && <Atribuicao atribuicao={atribuicaoDosVotos} />}
    </section>
  );
}

export default async function Deputado({ params, searchParams }) {
  const { id } = await params;
  const { pagina: paginaBruta } = await searchParams;
  const perfil = await buscarDeputado(id);
  if (!perfil) notFound();
  const historico = await buscarVotosDoDeputado(id, prepararPagina(paginaBruta));

  const { deputado, atribuicao } = perfil;
  return (
    <>
      <h1>{deputado.nome}</h1>
      <p className="identificacao">
        {`Identificador na Câmara dos Deputados: ${deputado.id_camara}.`}
      </p>
      <section aria-labelledby="deputado-na-camara" className="candidatura">
        <h2 id="deputado-na-camara">Na Câmara dos Deputados</h2>
        <dl>
          <Campo rotulo="Legislatura">{deputado.legislatura}</Campo>
          <Campo rotulo="UF">{deputado.uf}</Campo>
          <Campo rotulo="Partido">{deputado.partido}</Campo>
        </dl>
        <Atribuicao atribuicao={atribuicao} />
      </section>
      <Votos caminho={`/deputados/${id}/`} historico={historico} />
    </>
  );
}
