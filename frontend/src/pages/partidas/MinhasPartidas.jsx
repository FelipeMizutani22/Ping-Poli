import { Badge, Button, Card, Table } from "react-bootstrap";
import { Link, useNavigate } from "react-router-dom";

import { listarPartidas } from "../../api/partidas";
import AlertaErro from "../../components/AlertaErro";
import BadgeStatus from "../../components/BadgeStatus";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import PlacarSets from "../../components/PlacarSets";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData } from "../../utils/formatacao";
import { perspectiva } from "../../utils/partidas";

// Minhas partidas: as que registrei e as que foram registradas contra mim (UC15)
export default function MinhasPartidas() {
  const { usuario } = useAuth();
  const navigate = useNavigate();
  const { dados: partidas, carregando, erro } = useApi(() => listarPartidas({ escopo: "minhas" }), []);

  return (
    <Card>
      <Card.Body>
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h1 className="h4 mb-0">Minhas partidas</h1>
          <Button as={Link} to="/partidas/nova">Registrar partida</Button>
        </div>

        {carregando && <Carregando />}
        <AlertaErro erro={erro} />
        {partidas && partidas.length === 0 && (
          <EstadoVazio mensagem="Você ainda não tem partidas registradas."
            acao={<Button as={Link} to="/partidas/nova" variant="outline-primary">Registrar a primeira</Button>} />
        )}

        {partidas && partidas.length > 0 && (
          <Table hover responsive className="align-middle">
            <thead>
              <tr>
                <th>Data</th>
                <th>Adversário</th>
                <th>Competição</th>
                <th>Placar</th>
                <th>Sets</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {partidas.map((p) => {
                const v = perspectiva(p, usuario.id);
                return (
                  <tr key={p.id} role="button" onClick={() => navigate(`/partidas/${p.id}`)}>
                    <td>{formatarData(p.data_jogo)}</td>
                    <td>
                      {v.oponenteNome}
                      {p.tipo_adversario === "externo" && <Badge bg="light" text="dark" className="ms-1">Externo</Badge>}
                    </td>
                    <td>{p.competicao.nome}</td>
                    <td>
                      <Badge bg={v.venceu ? "primary" : "secondary"} className="me-1">{v.venceu ? "V" : "D"}</Badge>
                      {v.setsPro}–{v.setsContra}
                    </td>
                    <td className="small"><PlacarSets sets={p.sets} inverter={v.souAdversario} /></td>
                    <td><BadgeStatus status={p.status} /></td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card.Body>
    </Card>
  );
}
