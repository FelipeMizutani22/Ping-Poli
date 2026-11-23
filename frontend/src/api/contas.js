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

// Solicitação de cadastro (UC02) · rota pública
export const solicitarCadastro = (dados) => apiFetch("cadastro/", { method: "POST", body: dados });

// Meu perfil (UC04)
export const buscarPerfil = () => apiFetch("perfil/");
export const atualizarPerfil = (dados) => apiFetch("perfil/", { method: "PATCH", body: dados });
export const trocarSenha = (dados) => apiFetch("perfil/senha/", { method: "POST", body: dados });

// Editar dados de um membro pelo Diretor (UC03-b)
export const editarAtleta = (id, dados) => apiFetch(`atletas/${id}/`, { method: "PATCH", body: dados });