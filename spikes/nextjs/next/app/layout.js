export const metadata = { title: "polis — transparência e inteligência cívica" };

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <nav>
          <a href="/">Início</a> <a href="/busca/">Busca</a>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
