import { apiFetch } from './client';

export const buscarDesempenho = (params) => apiFetch('desempenho/', { params });

export const buscarEquipe = (params) => apiFetch('desempenho/equipe/', { params });

export const buscarConfronto = (params) => apiFetch('desempenho/confronto/', { params });
