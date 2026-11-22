import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";

// Telas administrativas: um Atleta que tentar entrar volta para o início.
export default function RotaDiretor() {
  const { ehDiretor } = useAuth();
  return ehDiretor ? <Outlet /> : <Navigate to="/" replace />;
}
