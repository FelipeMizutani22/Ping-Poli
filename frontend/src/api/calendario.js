import { apiFetch } from "./client";

// Trilha C · calendário e eventos (03_CONTRATO_API §3)
export const listarCalendario = (params) => apiFetch("calendario/", { params }); // { inicio, fim, tipo }
export const buscarEvento = (id) => apiFetch(`eventos/${id}/`);
export const criarEvento = (dados) => apiFetch("eventos/", { method: "POST", body: dados });
export const editarEvento = (id, dados) => apiFetch(`eventos/${id}/`, { method: "PATCH", body: dados });
export const cancelarEvento = (id, motivo) => apiFetch(`eventos/${id}/cancelar/`, { method: "POST", body: { motivo } });
export const listarPresencas = (id) => apiFetch(`eventos/${id}/presencas/`); // { evento, janela, dentro_da_janela, presencas }
export const registrarPresencas = (id, atletas = []) =>
  apiFetch(`eventos/${id}/presencas/`, { method: "POST", body: { atletas } }); // [] = eu mesmo
export const removerPresenca = (id, atletaId) => apiFetch(`eventos/${id}/presencas/${atletaId}/`, { method: "DELETE" });
