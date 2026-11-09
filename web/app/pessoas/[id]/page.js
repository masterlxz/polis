import { notFound } from "next/navigation";

import { buscarPerfil } from "../../../lib/api.js";
import { dataBr } from "../../../lib/formatar.js";
import Atribuicao from "./Atribuicao.js";

// Sem cache: quem a fonte retirar (lápide, ADR 0005) precisa sumir na hora.
export const dynamic = "force-dynamic";

const DESCRITOR = "polis: transparência e inteligência cívica";

export async function generateMetadata({ params }) {
  const { id } = await params;
  const perfil = await buscarPerfil(id);
  const titulo = perfil ? perfil.pessoa.nome : "Pessoa não encontrada";
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

function Candidatura({ candidatura }) {
  const { eleicao, partido, federacao, coligacao } = candidatura;
  const idDoTitulo = `candidatura-${eleicao.codigo}-${eleicao.turno}`;
  const data = dataBr(eleicao.data);
  return (
    <section aria-labelledby={idDoTitulo} className="candidatura">
      <h2 id={idDoTitulo}>{`${candidatura.cargo}, ${eleicao.turno}º turno`}</h2>
      <dl>
        <Campo rotulo="Eleição">
          {data ? `${eleicao.descricao} (${data})` : eleicao.descricao}
        </Campo>
        <Campo rotulo="Cargo">{candidatura.cargo}</Campo>
        <Campo rotulo="Abrangência">{candidatura.abrangencia}</Campo>
        <Campo rotulo="UF">{candidatura.uf}</Campo>
        <Campo rotulo="Unidade eleitoral">{candidatura.unidade_eleitoral?.nome}</Campo>
        <Campo rotulo="Número de urna">{candidatura.numero_urna}</Campo>
        <Campo rotulo="Partido">{`${partido.sigla}: ${partido.nome}`}</Campo>
        <Campo rotulo="Federação">
          {federacao && `${federacao.sigla}: ${federacao.nome}`}
        </Campo>
        <Campo rotulo="Coligação">{coligacao?.nome}</Campo>
        <Campo rotulo="Composição da coligação">{coligacao?.composicao}</Campo>
        <Campo rotulo="Situação">{candidatura.situacao}</Campo>
        <Campo rotulo="Resultado">{candidatura.resultado}</Campo>
      </dl>
      <Atribuicao atribuicao={candidatura.atribuicao} />
    </section>
  );
}

export default async function Pessoa({ params }) {
  const { id } = await params;
  const perfil = await buscarPerfil(id);
  if (!perfil) notFound();

  const { pessoa, candidaturas } = perfil;
  return (
    <>
      <h1>{pessoa.nome}</h1>
      <p className="identificacao">
        {`Ciclo eleitoral ${pessoa.ciclo}. Identificador no TSE (SQ_CANDIDATO): ${pessoa.id_tse}.`}
      </p>
      {candidaturas.map((candidatura) => (
        <Candidatura
          key={`${candidatura.eleicao.codigo}-${candidatura.eleicao.turno}`}
          candidatura={candidatura}
        />
      ))}
    </>
  );
}
