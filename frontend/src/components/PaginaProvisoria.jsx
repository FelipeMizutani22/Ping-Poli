import { Card } from "react-bootstrap";

// Página provisória criada na Fundação (F2). Cada trilha substitui pelo conteúdo real.
export default function PaginaProvisoria({ titulo, uc }) {
  return (
    <Card className="destaque-amarelo">
      <Card.Body>
        <h2 className="h4">{titulo}</h2>
        <p className="text-muted mb-0">Em construção — {uc}</p>
      </Card.Body>
    </Card>
  );
}
