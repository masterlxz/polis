import Link from "next/link";
import { notFound } from "next/navigation";

import { buscarVotacaoDaCamara } from "../../../../lib/api.js";
import {
  ROTULO_DA_APROVACAO,
  SEM_LISTA_NOMINAL,
  SEM_POSICAO,
  tituloDaVotacao,
  TOTAIS_ZERADOS,
  totaisInformados,
} from "../../../../lib/camara.js";
import { dataBr } from "../../../../lib/formatar.js";
import Atribuicao from "../../../pessoas/[id]/Atribuicao.js";
import Ementa from "../../Ementa.js";
import Nota from "../../Nota.js";

// Sem cache: o que a fonte corrigir precisa aparecer na hora.
export const dynamic = "force-dynamic";

const DESCRITOR = "polis: transparência e inteligência cívica";

export async function generateMetadata({ params }) {
  const { id } = await params;
  const detalhe = await buscarVotacaoDaCamara(id);
  const titulo = detalhe ? `Votação de ${tituloDaVotacao(detalhe.votacao)}` : "Votação não encontrada";
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

function Totais({ linhas }) {
  return (
    <table className="tabela">
      <caption>Totais informados pela Câmara</caption>
      <tbody>
        {linhas.map(([rotulo, valor]) => (
          <tr key={rotulo}>
            <td>{rotulo}</td>
            <td>{valor}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Contagem({ contagem }) {
  return (
    <table className="tabela">
      <caption>Contagem por voto, contado pelo polis a partir dos votos</caption>
      <thead>
        <tr>
          <th scope="col">Voto</th>
          <th scope="col">Deputados</th>
        </tr>
      </thead>
      <tbody>
        {contagem.map((item) => (
          <tr key={item.voto ?? ""}>
            <td>{item.voto ?? SEM_POSICAO}</td>
            <td>{item.quantidade}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// O nome só vem para quem tem `Deputy` (ADR 0032, decisão 7); sem perfil, só o id da Câmara.
function Votantes({ votos }) {
  return (
    <table className="tabela">
      <caption>Votos</caption>
      <thead>
        <tr>
          <th scope="col">Nome</th>
          <th scope="col">Partido</th>
          <th scope="col">Voto</th>
        </tr>
      </thead>
      <tbody>
        {votos.map((item) => (
          <tr key={`${item.legislatura}-${item.id_camara}`}>
            <td>
              {item.tem_perfil ? (
                <Link href={`/deputados/${item.legislatura}-${item.id_camara}/`}>{item.nome}</Link>
              ) : (
                `Deputado sem perfil (id ${item.id_camara})`
              )}
            </td>
            <td>{item.partido}</td>
            <td>{item.voto ?? SEM_POSICAO}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Todas as proposições, na ordem que a API manda (ADR 0032, emenda 5). Título e ementa são texto
// livre da fonte: o React os escapa. `origem` não aparece (sem significado verificado). O id da
// Câmara só aparece no endereço do link da tramitação, e só quando a proposição tem alguma em 2026
// (`total_tramitacoes`, emenda 6; ADR 0035): sem isso o link levaria a uma página vazia.
function Proposicoes({ proposicoes }) {
  return (
    <>
      <h2>Proposições</h2>
      <ul className="proposicoes">
        {proposicoes.map((item, indice) => (
          // A key é o índice (lista fixa, sem reordenação): `origem` e o id vazariam no payload do React.
          <li key={indice}>
            <strong>{item.titulo}</strong>
            {item.ementa && <Ementa texto={item.ementa} />}
            {item.total_tramitacoes > 0 && (
              <p>
                <Link href={`/camara/proposicoes/${item.id_camara}/`}>
                  {`Ver tramitação (${item.total_tramitacoes})`}
                </Link>
              </p>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

export default async function VotacaoDaCamara({ params }) {
  const { id } = await params;
  const detalhe = await buscarVotacaoDaCamara(id);
  if (!detalhe) notFound();

  const {
    votacao,
    votos,
    contagem_por_voto: contagem,
    atribuicao,
    atribuicao_dos_votos: atribuicaoDosVotos,
    proposicoes,
    atribuicao_das_proposicoes: atribuicaoDasProposicoes,
  } = detalhe;
  const temVotos = votos.length > 0;
  const totais = totaisInformados(votacao.totais_da_fonte);

  return (
    <>
      <h1>{`Votação de ${tituloDaVotacao(votacao)}`}</h1>
      <dl>
        <Campo rotulo="Data">{dataBr(votacao.data) ?? votacao.data}</Campo>
        <Campo rotulo="Órgão">{votacao.orgao}</Campo>
        <Campo rotulo={ROTULO_DA_APROVACAO}>{votacao.aprovacao}</Campo>
      </dl>
      {votacao.descricao && <p className="ementa">{votacao.descricao}</p>}
      <Nota aprovacao={votacao.aprovacao !== null} siglas={temVotos} />

      {!temVotos && (
        <p className="aviso">
          {totais === null ? `${SEM_LISTA_NOMINAL} ${TOTAIS_ZERADOS}` : SEM_LISTA_NOMINAL}
        </p>
      )}
      {totais && <Totais linhas={totais} />}
      {temVotos && <Contagem contagem={contagem} />}
      {proposicoes.length > 0 && <Proposicoes proposicoes={proposicoes} />}
      {temVotos && <Votantes votos={votos} />}
      <Atribuicao atribuicao={atribuicao} />
      {atribuicaoDosVotos && <Atribuicao atribuicao={atribuicaoDosVotos} />}
      {atribuicaoDasProposicoes && <Atribuicao atribuicao={atribuicaoDasProposicoes} />}
    </>
  );
}
