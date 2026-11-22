import { apiFetch } from "./client";

// Trilha A · contas (03_CONTRATO_API §1)
export const listarCursos = () => apiFetch("cursos/");
export const buscarAtletasOpcoes = (q, incluirInativos = false) =>
  apiFetch("atletas/opcoes/", { params: { q, incluir_inativos: incluirInativos ? 1 : undefined } });


// Gestão de atletas pelo Diretor (UC03)
export const listarAtletas = (params) => apiFetch("atletas/", { params });
export const aprovarAtleta = (id) => apiFetch(`atletas/${id}/aprovar/`, { method: "POST" });
export const recusarAtleta = (id, motivo) => apiFetch(`atletas/${id}/recusar/`, { method: "POST", body: { motivo } });
export const inativarAtleta = (id, justificativa) =>
  apiFetch(`atletas/${id}/inativar/`, { method: "POST", body: { justificativa } });
export const reativarAtleta = (id) => apiFetch(`atletas/${id}/reativar/`, { method: "POST" });
export const mudarPapel = (id, papel) => apiFetch(`atletas/${id}/papel/`, { method: "POST", body: { papel } });

