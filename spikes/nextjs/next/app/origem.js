export default function Origem({ p }) {
  return (
    <p className="origem">
      Fonte: <a href={p.url_fonte}>{p.fonte}</a>, coletado em {p.coletado_em}
    </p>
  );
}
