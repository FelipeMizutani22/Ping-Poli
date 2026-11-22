import { apiFetch } from "./client";

export const login = (email, senha) => apiFetch("auth/login/", { method: "POST", body: { email, senha } });
export const logout = () => apiFetch("auth/logout/", { method: "POST" });
export const buscarMe = () => apiFetch("auth/me/");
