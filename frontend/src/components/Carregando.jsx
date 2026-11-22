import { Spinner } from "react-bootstrap";

export default function Carregando({ texto = "Carregando..." }) {
  return (
    <div className="d-flex justify-content-center align-items-center gap-2 py-5 text-muted">
      <Spinner animation="border" size="sm" /> {texto}
    </div>
  );
}
