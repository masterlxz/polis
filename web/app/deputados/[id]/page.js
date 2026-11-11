import { notFound } from "next/navigation";

import { buscarDeputado } from "../../../lib/api.js";
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

export default async function Deputado({ params }) {
  const { id } = await params;
  const perfil = await buscarDeputado(id);
  if (!perfil) notFound();

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
    </>
  );
}
