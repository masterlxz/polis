# Imagem do front-end (ADR 0015). Next.js, React e Node estão fixados em package.json e na tag
# abaixo; a imagem de produção depende da decisão de hospedagem (P-04) e pode mudar.
FROM node:24-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
# Sem scripts de instalação: nenhum pacote roda código na instalação.
RUN npm ci --ignore-scripts
COPY next.config.mjs ./
COPY app app
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
