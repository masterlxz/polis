import Link from "next/link";
import { notFound } from "next/navigation";

import { buscarSenador, buscarVotosDoSenador, prepararPagina } from "../../../../lib/api.js";
import { dataBr, dataHoraBrasilia } from "../../../../lib/formatar.js";
import {
  NOTA_DA_SIGLA,
  descreverSigla,
  partidoParaExibir,
  siglaConhecida,
} from "../../../../lib/siglas.js";
import Atribuicao from "../../../pessoas/[id]/Atribuicao.js";

// Sem cache: quem a fonte tirar da lista de exercício precisa aparecer na hora (ADR 0027).
export const dynamic = "force-dynamic";

const DESCRITOR = "polis: transparência e inteligência cívica";

export async function generateMetadata({ params }) {
  const { codigo } = await params;
  const perfil = await buscarSenador(codigo);
  const titulo = perfil ? perfil.senador.nome : "Senador não encontrado";
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

// A data é a da COLETA em que o senador não veio mais, não a do fim do mandato, e a lista não diz
// o motivo (ADR 0027 e 0028).
function Situacao({ senador }) {
  if (senador.em_exercicio) return <Campo rotulo="Situação">Em exercício</Campo>;
  const coleta = senador.saiu_da_lista_em ? dataHoraBrasilia(senador.saiu_da_lista_em) : null;
  return (
    <>
      <Campo rotulo="Situação">Fora da lista de exercício</Campo>
      <Campo rotulo="Deixou de constar na coleta de">{coleta}</Campo>
    </>
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

// Na votação secreta a coluna traz `participacao` ("Votou"): diz que votou, não como (ADR 0029).
// Partido e UF são os do momento do voto, não os do perfil.
function Votos({ caminho, historico }) {
  const { votos, pagina, total_paginas: totalPaginas, atribuicao } = historico;
  const temSiglaNova = votos.some((item) => !siglaConhecida(item.voto ?? item.participacao));
  return (
    <section aria-labelledby="senador-votos" className="candidatura">
      <h2 id="senador-votos">Votos</h2>
      {votos.length === 0 ? (
        <SemVotos caminho={caminho} totalPaginas={totalPaginas} />
      ) : (
        <table className="tabela">
          <caption>Votos no Senado, da votação mais recente para a mais antiga</caption>
          <thead>
            <tr>
              <th scope="col">Votação</th>
              <th scope="col">Data</th>
              <th scope="col">Partido (à época)</th>
              <th scope="col">UF (à época)</th>
              <th scope="col">Voto ou situação</th>
            </tr>
          </thead>
          <tbody>
            {votos.map((item) => (
              <tr key={item.codigo}>
                <td>
                  <Link href={`/senado/votacoes/${item.codigo}/`}>{item.identificacao}</Link>
                  {item.ementa && <p className="ementa">{item.ementa}</p>}
                </td>
                <td>{dataBr(item.data) ?? item.data}</td>
                <td>{partidoParaExibir(item.partido)}</td>
                <td>{item.uf}</td>
                <td>{descreverSigla(item.voto ?? item.participacao)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {temSiglaNova && <p className="nota">{NOTA_DA_SIGLA}</p>}
      <Navegacao caminho={caminho} pagina={pagina} totalPaginas={totalPaginas} />
      {atribuicao && <Atribuicao atribuicao={atribuicao} />}
    </section>
  );
}

export default async function Senador({ params, searchParams }) {
  const { codigo } = await params;
  const { pagina: paginaBruta } = await searchParams;
  const perfil = await buscarSenador(codigo);
  if (!perfil) notFound();
  const historico = await buscarVotosDoSenador(codigo, prepararPagina(paginaBruta));

  const { senador, atribuicao } = perfil;
  return (
    <>
      <h1>{senador.nome}</h1>
      <p className="identificacao">{`Código no Senado Federal: ${senador.id_senado}.`}</p>
      <section aria-labelledby="senador-no-senado" className="candidatura">
        <h2 id="senador-no-senado">No Senado Federal</h2>
        <dl>
          <Campo rotulo="UF">{senador.uf}</Campo>
          <Campo rotulo="Partido">{partidoParaExibir(senador.partido)}</Campo>
          <Situacao senador={senador} />
        </dl>
        {!senador.em_exercicio && (
          <p className="nota">
            A data é a da coleta do polis em que o senador deixou de constar na lista de exercício
            do Senado, não a do fim do mandato. A fonte não diz o motivo (licença, fim de mandato,
            renúncia, suplente que voltou).
          </p>
        )}
        <Atribuicao atribuicao={atribuicao} />
      </section>
      <Votos caminho={`/senado/senadores/${senador.id_senado}/`} historico={historico} />
    </>
  );
}
