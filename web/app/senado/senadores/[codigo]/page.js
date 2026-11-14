import { notFound } from "next/navigation";

import { buscarSenador } from "../../../../lib/api.js";
import { dataHoraBrasilia } from "../../../../lib/formatar.js";
import { partidoParaExibir } from "../../../../lib/siglas.js";
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

export default async function Senador({ params }) {
  const { codigo } = await params;
  const perfil = await buscarSenador(codigo);
  if (!perfil) notFound();

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
    </>
  );
}
