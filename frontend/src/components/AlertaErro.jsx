import { Alert } from "react-bootstrap";

export default function AlertaErro({ erro, onFechar }) {
  if (!erro) return null;
  const mensagem = typeof erro === "string" ? erro : erro.message;
  return (
    <Alert variant="danger" dismissible={Boolean(onFechar)} onClose={onFechar}>
      {mensagem}
    </Alert>
  );
}
