// Formatação de dado vindo da API. Tudo aqui trata a entrada como não confiável.

const NA_DATA_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

// "2026-10-04" vira "04/10/2026" sem passar por `Date`, para o fuso não mudar o dia.
export function dataBr(iso) {
  const partes = NA_DATA_ISO.exec(iso ?? "");
  return partes ? `${partes[3]}/${partes[2]}/${partes[1]}` : null;
}

const EM_BRASILIA = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

// Instante conhecido (a coleta) em horário de Brasília: "07/11/2026 às 23:17".
export function dataHoraBrasilia(iso) {
  const instante = new Date(iso);
  if (Number.isNaN(instante.getTime())) return null;
  const p = Object.fromEntries(EM_BRASILIA.formatToParts(instante).map((x) => [x.type, x.value]));
  if (p.hour === "00" && p.minute === "00") return `${p.day}/${p.month}/${p.year}`;
  return `${p.day}/${p.month}/${p.year} às ${p.hour}:${p.minute}`;
}

// Tramitação da Câmara (P-23): 28,2% das medidas estão em 00:00 de Brasília, quando por acaso
// seriam ~0,07%. A fonte provavelmente só informa a data, então 00:00 mostra só "07/05/2026".
// A regra olha o instante em Brasília (não o texto) e vale só aqui: `dataHoraBrasilia` segue
// mostrando 00:00, porque na coleta e no Senado ele é um instante real.
export function dataOuDataHoraBrasilia(iso) {
  const instante = new Date(iso);
  if (Number.isNaN(instante.getTime())) return null;
  const p = Object.fromEntries(EM_BRASILIA.formatToParts(instante).map((x) => [x.type, x.value]));
  const data = `${p.day}/${p.month}/${p.year}`;
  return p.hour === "00" && p.minute === "00" ? data : `${data} às ${p.hour}:${p.minute}`;
}

// Link vindo da fonte só é link se for http(s). `javascript:`, `data:`, `ftp:` e endereço sem
// esquema (`//host`) viram `null`, e quem chama mostra o texto sem `href`.
export function linkSeguro(url) {
  try {
    const endereco = new URL(url);
    return endereco.protocol === "https:" || endereco.protocol === "http:" ? endereco.href : null;
  } catch {
    return null;
  }
}
