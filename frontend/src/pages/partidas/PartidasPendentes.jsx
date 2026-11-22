import { Badge, Card, ListGroup } from "react-bootstrap";
import { Link } from "react-router-dom";

import { listarPartidas } from "../../api/partidas";
import AlertaErro from "../../components/AlertaErro";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import PlacarSets from "../../components/PlacarSets";
import { useApi } from "../../hooks/useApi";
import { formatarData } from "../../utils/formatacao";

// UC16 · Partidas aguardando a MINHA confirmação (eu sou o adversário)
export default function PartidasPendentes() {
  const { dados: partidas, carregando, erro } = useApi(() => listarPartidas({ escopo: "pendentes" }), []);

  return (
    <Card>
      <Card.Body>
        <h1 className="h4 mb-3">Partidas pendentes</h1>
        {carregando && <Carregando />}
        <AlertaErro erro={erro} />
        {partidas && partidas.length === 0 && (
          <EstadoVazio mensagem="Você não tem partidas aguardando confirmação" />
        )}
        {partidas && partidas.length > 0 && (
          <ListGroup>
            {partidas.map((p) => {
              const euVenci = p.vencedor === "adversario";
              return (
                <ListGroup.Item key={p.id} action as={Link} to={`/partidas/${p.id}`}
                  className="d-flex flex-wrap justify-content-between align-items-center gap-2">
                  <div>
                    <div className="fw-semibold">{p.atleta.nome} registrou uma partida contra você</div>
                    <div className="small text-muted">
                      {formatarData(p.data_jogo)} · {p.competicao.nome} ·{" "}
                      <PlacarSets sets={p.sets} inverter /> · vencedor: {euVenci ? "você" : p.atleta.nome}
                    </div>
                  </div>
                  <Badge bg={p.dias_para_responder <= 2 ? "danger" : "warning"} text={p.dias_para_responder <= 2 ? undefined : "dark"}>
                    {p.dias_para_responder} {p.dias_para_responder === 1 ? "dia" : "dias"} para responder
                  </Badge>
                </ListGroup.Item>
              );
            })}
          </ListGroup>
        )}
      </Card.Body>
    </Card>
  );
}
