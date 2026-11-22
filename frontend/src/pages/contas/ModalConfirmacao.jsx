import { useState } from "react";
import { Button, Form, Modal } from "react-bootstrap";

import AlertaErro from "../../components/AlertaErro";

// Janela de confirmação reutilizável. Com `campo`, pede um texto (ex.: motivo da recusa).
// onConfirmar(texto) deve devolver uma Promise; se ela falhar, o erro aparece na própria janela.
export default function ModalConfirmacao({
  titulo, texto, campo, textoBotao = "Confirmar", variante = "primary", onConfirmar, onFechar,
}) {
  const [valor, setValor] = useState("");
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const faltaTexto = campo?.obrigatorio && !valor.trim();

  async function confirmar() {
    setErro(null);
    setEnviando(true);
    try {
      await onConfirmar(valor.trim());
    } catch (falha) {
      setErro(falha);
      setEnviando(false);
    }
  }

  return (
    <Modal show onHide={onFechar} centered>
      <Modal.Header closeButton>
        <Modal.Title className="h5">{titulo}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p>{texto}</p>
        {campo && (
          <Form.Group>
            <Form.Label>{campo.rotulo}{campo.obrigatorio && " *"}</Form.Label>
            <Form.Control as="textarea" rows={3} maxLength={campo.max || 300} value={valor}
              onChange={(e) => setValor(e.target.value)} autoFocus />
            <Form.Text muted>{valor.length}/{campo.max || 300}</Form.Text>
          </Form.Group>
        )}
        <div className="mt-3"><AlertaErro erro={erro} /></div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={onFechar} disabled={enviando}>Cancelar</Button>
        <Button variant={variante} onClick={confirmar} disabled={enviando || faltaTexto}>
          {enviando ? "Enviando..." : textoBotao}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}