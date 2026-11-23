import { apiFetch } from './client';

export { apiFetch };
export const listarCampeonatos = (params) => apiFetch('campeonatos/', { params });
export const buscarCampeonato = (id) => apiFetch(`campeonatos/${id}/`);
export const criarCampeonato = (body) => apiFetch('campeonatos/', { method: 'POST', body });
export const editarCampeonato = (id, body) => apiFetch(`campeonatos/${id}/`, { method: 'PATCH', body });
export const cancelarCampeonato = (id, motivo) => apiFetch(`campeonatos/${id}/cancelar/`, { method: 'POST', body: { motivo } });

export const minhasInscricoes = () => apiFetch('inscricoes/minhas/');
export const inscrever = (body) => apiFetch('inscricoes/', { method: 'POST', body });
export const cancelarInscricao = (id) => apiFetch(`inscricoes/${id}/`, { method: 'DELETE' });

export const listarInscritos = (id) => apiFetch(`campeonatos/${id}/inscricoes/`);
export const incluirInscrito = (id, body) => apiFetch(`campeonatos/${id}/inscricoes/`, { method: 'POST', body });
export const salvarResultados = (id, body) => apiFetch(`campeonatos/${id}/resultados/`, { method: 'PATCH', body });
export const removerInscrito = (id, motivo) => apiFetch(`inscricoes/${id}/remover/`, { method: 'POST', body: { motivo } });
