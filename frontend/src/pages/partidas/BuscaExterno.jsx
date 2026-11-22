import { useEffect, useState } from "react";
import { Alert, Button, Form, InputGroup, ListGroup, Row, Col } from "react-bootstrap";

import { buscarAdversariosExternos, cadastrarAdversarioExterno } from "../../api/partidas";

// UC15-a: busca entre os adversários externos e, se não existir, "Novo adversário externo".
export default function BuscaExterno({ valor, onSelect, isInvalid = false }) {
  const [termo, setTermo] = useState("");
  const [opcoes, setOpcoes] = useState([]);
  const [novo, setNovo] = useState(null); // { nome, clube } quando o formulário de cadastro está aberto
  const [erro, setErro] = useState(null);
  const [existente, setExistente] = useState(null);

  useEffect(() => {
    if (valor) return;
    const espera = setTimeout(() => {
      buscarAdversariosExternos(termo.trim()).then(setOpcoes).catch(() => setOpcoes([]));
    }, 300);
    return () => clearTimeout(espera);
  }, [termo, valor]);

  async function cadastrar() {
    setErro(null);
    setExistente(null);
    try {
      const criado = await cadastrarAdversarioExterno({ nome: novo.nome.trim(), clube: novo.clube.trim() });
      onSelect(criado);
      setNovo(null);
    } catch (e) {
      if (e.codigo === "ja_existe") setExistente(e.campos.existente); // UC15-j
      else setErro(e);
    }
  }

  if (valor) {
    return (
      <InputGroup>
        <Form.Control readOnly value={valor.clube ? `${valor.nome} (${valor.clube})` : valor.nome} />
        <Button variant="outline-secondary" onClick={() => { onSelect(null); setTermo(""); }}>Trocar</Button>
      </InputGroup>
    );
  }

  if (novo) {
    return (
      <div className="border rounded p-3 bg-light">
        <Row className="g-2">
          <Col sm={7}>
            <Form.Control placeholder="Nome (obrigatório)" maxLength={100} value={novo.nome}
              isInvalid={Boolean(erro?.campos?.nome)} onChange={(e) => setNovo({ ...novo, nome: e.target.value })} />
            <Form.Control.Feedback type="invalid">{erro?.campos?.nome}</Form.Control.Feedback>
          </Col>
          <Col sm={5}>
            <Form.Control placeholder="Clube/instituição (opcional)" maxLength={100} value={novo.clube}
              onChange={(e) => setNovo({ ...novo, clube: e.target.value })} />
          </Col>
        </Row>
        {existente && (
          <Alert variant="warning" className="mt-2 mb-0 py-2">
            {existente.nome}{existente.clube && ` (${existente.clube})`} já está cadastrado.{" "}
            <Button size="sm" variant="link" className="p-0 align-baseline"
              onClick={() => { onSelect(existente); setNovo(null); setExistente(null); }}>
              Selecionar este adversário
            </Button>
          </Alert>
        )}
        {erro && !erro.campos?.nome && <Alert variant="danger" className="mt-2 mb-0 py-2">{erro.message}</Alert>}
        <div className="mt-2 d-flex gap-2">
          <Button size="sm" onClick={cadastrar}>Cadastrar</Button>
          <Button size="sm" variant="outline-secondary" onClick={() => setNovo(null)}>Cancelar</Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Form.Control placeholder="Buscar adversário externo pelo nome" value={termo} isInvalid={isInvalid}
        onChange={(e) => setTermo(e.target.value)} />
      <ListGroup className="mt-1" style={{ maxHeight: 200, overflowY: "auto" }}>
        {opcoes.map((a) => (
          <ListGroup.Item action key={a.id} onClick={() => onSelect(a)}>
            {a.nome} {a.clube && <small className="text-muted">· {a.clube}</small>}
          </ListGroup.Item>
        ))}
      </ListGroup>
      <Button size="sm" variant="link" className="px-0" onClick={() => setNovo({ nome: termo, clube: "" })}>
        + Novo adversário externo
      </Button>
    </div>
  );
}
