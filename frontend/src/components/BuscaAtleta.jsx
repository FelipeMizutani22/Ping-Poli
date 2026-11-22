import { useEffect, useState } from "react";
import { Button, Form, InputGroup, ListGroup } from "react-bootstrap";

import { buscarAtletasOpcoes } from "../api/contas";

// Busca atletas ativos por nome ou NUSP (atletas/opcoes/). Usada por partidas, presença e confronto.
export default function BuscaAtleta({ valor, onSelect, incluirInativos = false, isInvalid = false }) {
  const [termo, setTermo] = useState("");
  const [opcoes, setOpcoes] = useState([]);
  const [aberto, setAberto] = useState(false);

  useEffect(() => {
    if (valor || termo.trim().length < 2) {
      setOpcoes([]);
      return;
    }
    const espera = setTimeout(() => {
      buscarAtletasOpcoes(termo.trim(), incluirInativos)
        .then((lista) => {
          setOpcoes(lista);
          setAberto(true);
        })
        .catch(() => setOpcoes([]));
    }, 300);
    return () => clearTimeout(espera);
  }, [termo, valor, incluirInativos]);

  if (valor) {
    return (
      <InputGroup>
        <Form.Control readOnly value={`${valor.nome} · NUSP ${valor.nusp}`} />
        <Button variant="outline-secondary" onClick={() => { onSelect(null); setTermo(""); }}>Trocar</Button>
      </InputGroup>
    );
  }

  return (
    <div className="position-relative">
      <Form.Control
        placeholder="Digite o nome ou o NUSP"
        value={termo}
        isInvalid={isInvalid}
        onChange={(e) => setTermo(e.target.value)}
        onFocus={() => setAberto(true)}
      />
      {aberto && termo.trim().length >= 2 && (
        <ListGroup className="position-absolute w-100 shadow-sm" style={{ zIndex: 10 }}>
          {opcoes.length === 0 && <ListGroup.Item className="text-muted">Nenhum atleta encontrado</ListGroup.Item>}
          {opcoes.map((a) => (
            <ListGroup.Item action key={a.id} onClick={() => { onSelect(a); setAberto(false); }}>
              {a.nome} <small className="text-muted">· NUSP {a.nusp}</small>
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
    </div>
  );
}
