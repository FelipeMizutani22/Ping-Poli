import { apiFetch } from "./client";

// Trilha D · funções de competicoes (03_CONTRATO_API). Ex.:
// export const listarAlgo = (params) => apiFetch("caminho/", { params });
export { apiFetch };

// Trilha D · campeonatos (03_CONTRATO_API §4). Usado também pelo formulário de partida (UC15).
export const listarCampeonatos = (params) => apiFetch("campeonatos/", { params });
