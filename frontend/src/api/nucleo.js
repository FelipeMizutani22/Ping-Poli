import { apiFetch } from "./client";

// Trilha A · núcleo: página inicial e notificações (03_CONTRATO_API §7)
export const buscarPainel = () => apiFetch("painel/");

export const listarNotificacoes = (apenasNaoLidas = false) =>
  apiFetch("notificacoes/", { params: { nao_lidas: apenasNaoLidas ? "1" : undefined } });
export const marcarNotificacaoLida = (id) => apiFetch(`notificacoes/${id}/lida/`, { method: "POST" });
export const marcarTodasLidas = () => apiFetch("notificacoes/marcar-todas/", { method: "POST" });

export { apiFetch };