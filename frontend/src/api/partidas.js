import { apiFetch } from "./client";

// Trilha B · partidas (03_CONTRATO_API §5)
export const listarPartidas = (params) => apiFetch("partidas/", { params });
export const buscarPartida = (id) => apiFetch(`partidas/${id}/`);
export const registrarPartida = (dados) => apiFetch("partidas/", { method: "POST", body: dados });
export const confirmarPartida = (id) => apiFetch(`partidas/${id}/confirmar/`, { method: "POST" });
export const contestarPartida = (id, dados) => apiFetch(`partidas/${id}/contestar/`, { method: "POST", body: dados });
export const moderarPartida = (id, dados) => apiFetch(`partidas/${id}/moderar/`, { method: "POST", body: dados });
export const historicoPartida = (id) => apiFetch(`partidas/${id}/historico/`);
export const buscarAdversariosExternos = (q) => apiFetch("adversarios-externos/", { params: { q } });
export const cadastrarAdversarioExterno = (dados) =>
  apiFetch("adversarios-externos/", { method: "POST", body: dados });
