import { apiFetch } from './client';

export const buscarDesempenho = (params) => apiFetch('desempenho/', { params });
