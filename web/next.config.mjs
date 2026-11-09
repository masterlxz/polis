/** @type {import('next').NextConfig} */
const nextConfig = {
  // Servidor Node autocontido: a imagem final não leva node_modules inteiro (ADR 0015, spike).
  // Mesmas URLs, com barra final, do Django (ADR 0015, spike).
  trailingSlash: true,
};

export default nextConfig;
