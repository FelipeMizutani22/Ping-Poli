import { Badge } from "react-bootstrap";

import { CORES_STATUS, rotulo } from "../utils/rotulos";

// grupo: chave de ROTULOS (ex.: "statusPartida", "situacao", "statusCampeonato")
export default function BadgeStatus({ status, grupo = "statusPartida" }) {
  const cor = CORES_STATUS[status] || "secondary";
  return (
    <Badge bg={cor} text={cor === "warning" ? "dark" : undefined}>
      {rotulo(grupo, status)}
    </Badge>
  );
}
