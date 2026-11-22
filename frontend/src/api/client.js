// Ponto único de acesso à API (04_FRONTEND §2). Nenhum componente chama fetch diretamente.
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1/";

export class ApiError extends Error {
  constructor(status, dados) {
    super(dados?.detail || "Serviço indisponível. Tente novamente em instantes");
    this.status = status; // 0 = falha de rede
    this.codigo = dados?.codigo; // ex.: "conta_pendente"
    this.campos = dados || {}; // { email: ["…"], sets: ["…"] }
  }
}

export async function apiFetch(caminho, { method = "GET", body, params } = {}) {
  const base = BASE.endsWith("/") ? BASE : BASE + "/";
  const url = new URL(base + caminho);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  const token = localStorage.getItem("pingpoli_token");
  let resp;
  try {
    resp = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", ...(token && { Authorization: `Token ${token}` }) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, null); // "Serviço indisponível. Tente novamente em instantes"
  }
  if (resp.status === 204) return null;
  const dados = await resp.json().catch(() => null);
  if (resp.status === 401) window.dispatchEvent(new Event("pingpoli:nao-autenticado"));
  if (!resp.ok) throw new ApiError(resp.status, dados);
  return dados;
}
