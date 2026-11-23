import { apiFetch } from './client';

export { apiFetch };
export const listarCampeonatos = (params) => apiFetch('campeonatos/', { params });
export const buscarCampeonato = (id) => apiFetch(`campeonatos/${id}/`);
export const criarCampeonato = (body) => apiFetch('campeonatos/', { method: 'POST', body });
export const editarCampeonato = (id, body) => apiFetch(`campeonatos/${id}/`, { method: 'PATCH', body });
export const cancelarCampeonato = (id, motivo) => apiFetch(`campeonatos/${id}/cancelar/`, { method: 'POST', body: { motivo } });
