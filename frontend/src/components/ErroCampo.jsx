import { Form } from "react-bootstrap";

// Mostra o erro que a API devolveu para um campo: erro.campos[campo] = ["mensagem", ...]
export default function ErroCampo({ erro, campo }) {
  const mensagens = erro?.campos?.[campo];
  if (!mensagens) return null;
  const lista = Array.isArray(mensagens) ? mensagens : [String(mensagens)];
  return (
    <Form.Control.Feedback type="invalid" className="d-block">
      {lista.map((m) => (
        <div key={m}>{m}</div>
      ))}
    </Form.Control.Feedback>
  );
}
