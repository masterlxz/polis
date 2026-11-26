import { textoDaNota, URL_DA_DOCUMENTACAO } from "../../lib/camara.js";

// A nota dos códigos da Câmara (`aprovacao` e siglas de voto): as legendas da documentação oficial
// que a página precisa, com o link dela. O texto vai num só nó, para o HTML não o partir em pedaços.
export default function Nota({ aprovacao, siglas }) {
  const texto = textoDaNota({ aprovacao, siglas });
  if (texto === null) return null;
  return (
    <p className="nota">
      {texto} Fonte: <a href={URL_DA_DOCUMENTACAO}>documentação da Câmara</a>.
    </p>
  );
}
