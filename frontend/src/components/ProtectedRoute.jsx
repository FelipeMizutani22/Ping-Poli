import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import Carregando from "./Carregando";

// Só deixa passar quem está logado; os outros vão para /login (e voltam para cá depois de entrar).
export default function ProtectedRoute() {
  const { usuario, carregando } = useAuth();
  const location = useLocation();
  if (carregando) return <Carregando />;
  if (!usuario) return <Navigate to="/login" replace state={{ de: location.pathname }} />;
  return <Outlet />;
}
