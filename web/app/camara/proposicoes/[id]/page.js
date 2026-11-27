import { notFound } from "next/navigation";

import { buscarProposicaoDaCamara } from "../../../../lib/api.js";
import { NOTA_DAS_TRAMITACOES, SEM_TRAMITACAO } from "../../../../lib/camara.js";
import { dataHoraBrasilia } from "../../../../lib/formatar.js";
import Atribuicao from "../../../pessoas/[id]/Atribuicao.js";
import Ementa from "../../Ementa.js";

// Sem cache: o que a fonte corrigir precisa aparecer na hora.
export const dynamic = "force-dynamic";

const DESCRITOR = "polis: transparência e inteligência cívica";

export async function generateMetadata({ params }) {
  const { id } = await params;
  const corpo = await buscarProposicaoDaCamara(id);
  const titulo = corpo ? corpo.proposicao.titulo : "Proposição não encontrada";
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

// Na ordem que a API manda (ADR 0035, decisão 5). A hora vem como instante com o deslocamento e é
// mostrada em Brasília (nunca cortando o texto). A `sequencia` não aparece: o significado dela não
// foi verificado e a ordem já a usa. Órgão e descrição são texto livre da fonte: o React os escapa.
function Tramitacoes({ tramitacoes }) {
  return (
    <table className="tabela">
      <caption>Tramitações</caption>
      <thead>
        <tr>
          <th scope="col">Data e hora</th>
          <th scope="col">Órgão</th>
          <th scope="col">Descrição</th>
        </tr>
      </thead>
      <tbody>
        {tramitacoes.map((item, indice) => (
          <tr key={indice}>
            <td>{dataHoraBrasilia(item.data_hora)}</td>
            <td>{item.orgao}</td>
            <td dangerouslySetInnerHTML={{ __html: item.descricao }} />
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default async function ProposicaoDaCamara({ params }) {
  const { id } = await params;
  const corpo = await buscarProposicaoDaCamara(id);
  if (!corpo) notFound();

  const {
    proposicao,
    tramitacoes,
    atribuicao_da_proposicao: atribuicaoDaProposicao,
    atribuicao_das_tramitacoes: atribuicaoDasTramitacoes,
  } = corpo;

  return (
    <>
      <h1>{proposicao.titulo}</h1>
      <dl>
        <Campo rotulo="Tipo">{proposicao.tipo}</Campo>
        <Campo rotulo="Número">{proposicao.numero}</Campo>
        <Campo rotulo="Ano">{proposicao.ano}</Campo>
      </dl>
      {proposicao.ementa && <Ementa texto={proposicao.ementa} />}
      <p className="nota">{NOTA_DAS_TRAMITACOES}</p>
      {tramitacoes.length > 0 ? (
        <Tramitacoes tramitacoes={tramitacoes} />
      ) : (
        <p className="aviso">{SEM_TRAMITACAO}</p>
      )}
      <Atribuicao atribuicao={atribuicaoDaProposicao} />
      {atribuicaoDasTramitacoes && <Atribuicao atribuicao={atribuicaoDasTramitacoes} />}
    </>
  );
}
