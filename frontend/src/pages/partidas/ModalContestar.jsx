import { useState } from "react";
import { Alert, Button, Form, Modal } from "react-bootstrap";

import { contestarPartida } from "../../api/partidas";
import ErroCampo from "../../components/ErroCampo";
import { linhasVazias, setsDasLinhas } from "../../utils/partidas";
import EntradaPlacar from "./EntradaPlacar";
import ErrosPlacar from "./ErrosPlacar";

// UC16-a · Contestar: justificativa (10 a 500) e, opcionalmente, o placar considerado correto.
// O placar vai no ponto de vista de quem registrou (pontos_atleta = registrante), como no resto da API.
export default function ModalContestar({ partida, mostrar, onFechar, onContestada }) {
  const [justificativa, setJustificativa] = useState("");
  const [informarPlacar, setInformarPlacar] = useState(false);
  const [linhas, setLinhas] = useState(linhasVazias(partida.formato));
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
    let sets = [];
    if (informarPlacar) {
      const r = setsDasLinhas(linhas);
      if (r.erro) {
        setErro({ campos: { sets: [r.erro] } });
        return;
      }
      sets = r.sets;
    }
    setEnviando(true);
    try {
      await contestarPartida(partida.id, { justificativa: justificativa.trim(), sets });
      onContestada();
    } catch (falha) {
      setErro(falha);
    } finally {
      setEnviando(false);
    }
  }

  const tamanho = justificativa.trim().length;
  return (
    <Modal show={mostrar} onHide={onFechar} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Contestar partida</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {erro?.message && !erro.campos?.justificativa && !erro.campos?.sets && <Alert variant="danger">{erro.message}</Alert>}
        <Form.Group className="mb-3" controlId="justificativa">
          <Form.Label>Justificativa *</Form.Label>
          <Form.Control as="textarea" rows={3} maxLength={500} value={justificativa}
            isInvalid={Boolean(erro?.campos?.justificativa)} onChange={(e) => setJustificativa(e.target.value)} />
          <Form.Text className={tamanho > 0 && tamanho < 10 ? "text-danger" : "text-muted"}>
            {tamanho}/500 caracteres (mínimo 10)
          </Form.Text>
          <ErroCampo erro={erro} campo="justificativa" />
        </Form.Group>
        <Form.Check id="informar-placar" type="switch" className="mb-2" label="Informar o placar que considero correto"
          checked={informarPlacar} onChange={(e) => setInformarPlacar(e.target.checked)} />
        {informarPlacar && (
          <>
            <EntradaPlacar linhas={linhas} onChange={setLinhas} rotuloAtleta={partida.atleta.nome} rotuloAdversario="Você" />
            <ErrosPlacar mensagens={erro?.campos?.sets} />
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={onFechar}>Cancelar</Button>
        <Button variant="danger" onClick={enviar} disabled={enviando || tamanho < 10}>
          {enviando ? "Enviando..." : "Enviar contestação"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
