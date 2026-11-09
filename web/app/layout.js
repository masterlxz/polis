import "./globals.css";

const DESCRITOR = "transparência e inteligência cívica";

// `noindex` em tudo: nada é público antes da validação do P-16 (ADR 0005). Abrir para os
// buscadores (PRD §12) é uma decisão explícita, na abertura ao público.
export const metadata = {
  title: `polis: ${DESCRITOR}`,
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <a className="pular" href="#conteudo">
          Pular para o conteúdo
        </a>
        <header className="topo">
          <p>
            <strong>polis</strong>: {DESCRITOR}
          </p>
          <nav aria-label="Principal">
            <a href="/busca/">Buscar</a>
          </nav>
        </header>
        <main id="conteudo" tabIndex={-1}>
          {children}
        </main>
        <footer className="rodape">
          <p>
            polis: {DESCRITOR}. Cada dado mostra a fonte e a data em que foi coletado.
          </p>
        </footer>
      </body>
    </html>
  );
}
