import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import RotaDiretor from "./components/RotaDiretor";
import NaoEncontrada from "./pages/NaoEncontrada";
import DetalheAviso from "./pages/avisos/DetalheAviso";
import FormAviso from "./pages/avisos/FormAviso";
import QuadroAvisos from "./pages/avisos/QuadroAvisos";
import Calendario from "./pages/calendario/Calendario";
import DetalheEvento from "./pages/calendario/DetalheEvento";
import FormEvento from "./pages/calendario/FormEvento";
import Frequencia from "./pages/calendario/Frequencia";
import DetalheCampeonato from "./pages/competicoes/DetalheCampeonato";
import FormCampeonato from "./pages/competicoes/FormCampeonato";
import ListaCampeonatos from "./pages/competicoes/ListaCampeonatos";
import Cadastro from "./pages/contas/Cadastro";
import GestaoAtletas from "./pages/contas/GestaoAtletas";
import Login from "./pages/contas/Login";
import Perfil from "./pages/contas/Perfil";
import Confronto from "./pages/desempenho/Confronto";
import Dashboard from "./pages/desempenho/Dashboard";
import Inicio from "./pages/inicio/Inicio";
import DetalhePartida from "./pages/partidas/DetalhePartida";
import FormPartida from "./pages/partidas/FormPartida";
import MinhasPartidas from "./pages/partidas/MinhasPartidas";
import Moderacao from "./pages/partidas/Moderacao";
import PartidasPendentes from "./pages/partidas/PartidasPendentes";

// Rotas do 04_FRONTEND §4. Cada trilha só troca o conteúdo das suas páginas.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Inicio />} />
          <Route path="/perfil" element={<Perfil />} />

          <Route path="/avisos" element={<QuadroAvisos />} />
          <Route path="/avisos/:id" element={<DetalheAviso />} />
          <Route path="/calendario" element={<Calendario />} />
          <Route path="/eventos/:id" element={<DetalheEvento />} />
          <Route path="/frequencia" element={<Frequencia />} />
          <Route path="/campeonatos" element={<ListaCampeonatos />} />
          <Route path="/campeonatos/:id" element={<DetalheCampeonato />} />

          <Route path="/partidas" element={<MinhasPartidas />} />
          <Route path="/partidas/nova" element={<FormPartida />} />
          <Route path="/partidas/pendentes" element={<PartidasPendentes />} />
          <Route path="/partidas/:id" element={<DetalhePartida />} />

          <Route path="/desempenho" element={<Dashboard />} />
          <Route path="/confronto" element={<Confronto />} />

          <Route element={<RotaDiretor />}>
            <Route path="/admin/atletas" element={<GestaoAtletas />} />
            <Route path="/avisos/novo" element={<FormAviso />} />
            <Route path="/avisos/:id/editar" element={<FormAviso />} />
            <Route path="/eventos/novo" element={<FormEvento />} />
            <Route path="/eventos/:id/editar" element={<FormEvento />} />
            <Route path="/campeonatos/novo" element={<FormCampeonato />} />
            <Route path="/campeonatos/:id/editar" element={<FormCampeonato />} />
            <Route path="/moderacao" element={<Moderacao />} />
          </Route>

          <Route path="*" element={<NaoEncontrada />} />
        </Route>
      </Route>
    </Routes>
  );
}
