import { apiFetch } from "./client";

// Trilha A · contas (03_CONTRATO_API §1)
export const listarCursos = () => apiFetch("cursos/");
export const buscarAtletasOpcoes = (q, incluirInativos = false) =>
  apiFetch("atletas/opcoes/", { params: { q, incluir_inativos: incluirInativos ? 1 : undefined } });
