import { dataHoraBrasilia, linkSeguro } from "../../../lib/formatar.js";

// Origem de cada dado (ADR 0015, decisão 5; PRD §7.3). Link que a fonte forneça só vira link se
// for http(s); qualquer outra coisa aparece como texto. A data de geração pela fonte não é
// mostrada: o fuso do TSE ainda não foi verificado.
export default function Atribuicao({ atribuicao }) {
  const { fonte, conjunto, coletado_em: coletadoEm, url_origem: urlOrigem, licenca } = atribuicao;
  const coleta = dataHoraBrasilia(coletadoEm);
  const linkOrigem = linkSeguro(urlOrigem);
  const linkLicenca = linkSeguro(licenca?.url);

  return (
    <section className="origem" aria-label="Origem dos dados">
      <h3>Origem dos dados</h3>
      <dl>
        <div>
          <dt>Fonte</dt>
          <dd>{fonte}</dd>
        </div>
        <div>
          <dt>Conjunto de dados</dt>
          <dd>{conjunto}</dd>
        </div>
        {coleta && (
          <div>
            <dt>Coletado em</dt>
            <dd>{coleta}</dd>
          </div>
        )}
        {urlOrigem && (
          <div>
            <dt>Original</dt>
            <dd>
              {linkOrigem ? <a href={linkOrigem}>Arquivo original na fonte</a> : urlOrigem}
            </dd>
          </div>
        )}
        {licenca?.id && (
          <div>
            <dt>Licença</dt>
            <dd>{linkLicenca ? <a href={linkLicenca}>{licenca.id}</a> : licenca.id}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}
