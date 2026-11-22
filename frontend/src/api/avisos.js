import { apiFetch } from "./client";

// Trilha C · avisos (03_CONTRATO_API §2)
export const listarAvisos = (params) => apiFetch("avisos/", { params });
export const buscarAviso = (id) => apiFetch(`avisos/${id}/`); // também marca o aviso como lido
export const publicarAviso = (dados) => apiFetch("avisos/", { method: "POST", body: dados });
export const editarAviso = (id, dados) => apiFetch(`avisos/${id}/`, { method: "PATCH", body: dados });
export const excluirAviso = (id) => apiFetch(`avisos/${id}/`, { method: "DELETE" });
export const alternarFixado = (id) => apiFetch(`avisos/${id}/fixar/`, { method: "POST" });
