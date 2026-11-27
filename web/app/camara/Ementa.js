import { resumoDaEmenta } from "../../lib/camara.js";

// Ementa curta sai inteira. Longa: o resumo fica visível e o texto inteiro vai num `<details>`
// nativo (abre sem JavaScript, acessível por teclado). O texto aparece nos dois por escolha: o
// resumo fora do botão mantém a lista legível. Usada na votação e na proposição (ADR 0035).
export default function Ementa({ texto }) {
  const resumo = resumoDaEmenta(texto);
  if (resumo === null) return <p className="ementa">{texto}</p>;
  return (
    <>
      <p className="ementa">{resumo}</p>
      <details>
        <summary>Ler a ementa inteira</summary>
        <p className="ementa">{texto}</p>
      </details>
    </>
  );
}
