import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { buscarMe, login, logout } from "../api/auth";

const AuthContext = createContext(null);
const CHAVE_TOKEN = "pingpoli_token";

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const navigate = useNavigate();

  const limpar = useCallback(() => {
    localStorage.removeItem(CHAVE_TOKEN);
    setUsuario(null);
  }, []);

  // UC01-d: ao abrir o app com um token salvo, recupera o usuário; se o token não vale mais, limpa tudo.
  useEffect(() => {
    if (!localStorage.getItem(CHAVE_TOKEN)) {
      setCarregando(false);
      return;
    }
    buscarMe()
      .then(setUsuario)
      .catch(limpar)
      .finally(() => setCarregando(false));
  }, [limpar]);

  // Qualquer resposta 401 da API (token expirado ou apagado) leva de volta ao login.
  useEffect(() => {
    const aoPerderSessao = () => {
      limpar();
      navigate("/login", { replace: true });
    };
    window.addEventListener("pingpoli:nao-autenticado", aoPerderSessao);
    return () => window.removeEventListener("pingpoli:nao-autenticado", aoPerderSessao);
  }, [limpar, navigate]);

  async function entrar(email, senha) {
    const { token, atleta } = await login(email, senha);
    localStorage.setItem(CHAVE_TOKEN, token);
    setUsuario(atleta);
    return atleta;
  }

  async function sair() {
    try {
      await logout();
    } catch {
      // mesmo se a API falhar, a sessão local é encerrada
    }
    limpar();
    navigate("/login", { replace: true });
  }

  async function recarregarUsuario() {
    setUsuario(await buscarMe());
  }

  const valor = {
    usuario,
    carregando,
    ehDiretor: usuario?.papel === "diretor",
    entrar,
    sair,
    recarregarUsuario,
  };
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
