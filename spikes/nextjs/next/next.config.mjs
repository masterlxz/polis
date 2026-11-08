/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Mesmas URLs (com barra final) do Django, para a comparação não medir redirecionamentos.
  trailingSlash: true,
};
export default nextConfig;
