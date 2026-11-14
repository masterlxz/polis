import Link from "next/link";
import { notFound } from "next/navigation";

import { buscarVotacaoDoSenado } from "../../../../lib/api.js";
import { dataBr } from "../../../../lib/formatar.js";
import {
  NOTA_DA_SIGLA,
  NOTA_DO_RESULTADO,
  descreverSigla,
  partidoParaExibir,
  resultadoParaExibir,
  siglaConhecida,
} from "../../../../lib/siglas.js";
import Atribuicao from "../../../pessoas/[id]/Atribuicao.js";

// Sem cache: o que a fonte corrigir precisa aparecer na hora.
export const dynamic = "force-dynamic";

const DESCRITOR = "polis: transparência e inteligência cívica";

export async function generateMetadata({ params }) {
  const { codigo } = await params;
  const detalhe = await buscarVotacaoDoSenado(codigo);
  const titulo = detalhe ? detalhe.votacao.identificacao : "Votação não encontrada";
  return { title: `${titulo} | ${DESCRITOR}` };
}

// Na secreta a coluna é "Situação": a sigla `Votou` diz que o senador votou, não como (ADR 0029).
function Contagem({ contagem, rotuloDaColuna }) {
  return (
    <table className="tabela">
      <caption>Contagem por sigla, contado pelo polis a partir dos votos</caption>
      <thead>
        <tr>
          <th scope="col">{rotuloDaColuna}</th>
          <th scope="col">Senadores</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(contagem).map(([sigla, quantidade]) => (
          <tr key={sigla}>
            <td>{descreverSigla(sigla)}</td>
            <td>{quantidade}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TotaisDoSenado({ totais }) {
  const linhas = [
    ["Sim", totais.sim],
    ["Não", totais.nao],
    ["Abstenção", totais.abstencao],
  ];
  return (
    <table className="tabela">
      <caption>Resultado: total informado pelo Senado</caption>
      <tbody>
        {linhas.map(([rotulo, valor]) => (
          <tr key={rotulo}>
            <td>{rotulo}</td>
            <td>{valor ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Votantes({ itens, rotuloDaColuna, titulo }) {
  return (
    <table className="tabela">
      <caption>{titulo}</caption>
      <thead>
        <tr>
          <th scope="col">Nome</th>
          <th scope="col">Partido</th>
          <th scope="col">UF</th>
          <th scope="col">{rotuloDaColuna}</th>
        </tr>
      </thead>
      <tbody>
        {itens.map((item) => (
          <tr key={item.id_senado}>
            <td>
              {item.tem_perfil ? (
                <Link href={`/senado/senadores/${item.id_senado}/`}>{item.nome}</Link>
              ) : (
                item.nome
              )}
            </td>
            <td>{partidoParaExibir(item.partido)}</td>
            <td>{item.uf}</td>
            <td>{descreverSigla(item.sigla)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default async function VotacaoDoSenado({ params }) {
  const { codigo } = await params;
  const detalhe = await buscarVotacaoDoSenado(codigo);
  if (!detalhe) notFound();

  const { votacao, contagem_por_sigla: contagem, atribuicao } = detalhe;
  const itens = votacao.secreta ? detalhe.participacao : detalhe.votos;
  const coluna = votacao.secreta ? "Situação" : "Voto";
  const resultado = resultadoParaExibir(votacao.resultado);
  const temSiglaNova = itens.some((item) => !siglaConhecida(item.sigla));

  return (
    <>
      <h1>{votacao.identificacao}</h1>
      <dl>
        <div>
          <dt>Data</dt>
          <dd>{dataBr(votacao.data) ?? votacao.data}</dd>
        </div>
        <div>
          <dt>Resultado</dt>
          <dd>{resultado.completo}</dd>
        </div>
      </dl>
      {resultado.inferido && <p className="nota">{NOTA_DO_RESULTADO}</p>}
      {votacao.ementa && <p className="ementa">{votacao.ementa}</p>}

      {votacao.secreta && (
        <p className="aviso">
          Votação secreta: o Senado não divulga o voto de cada senador. A lista mostra só quem votou
          e quem esteve ausente ou impedido.
        </p>
      )}
      {votacao.secreta && <TotaisDoSenado totais={votacao.totais_da_fonte} />}
      <Contagem contagem={contagem} rotuloDaColuna={coluna} />
      {temSiglaNova && <p className="nota">{NOTA_DA_SIGLA}</p>}
      <Votantes
        itens={itens}
        rotuloDaColuna={coluna}
        titulo={votacao.secreta ? "Participação" : "Votos"}
      />
      <Atribuicao atribuicao={atribuicao} />
    </>
  );
}
