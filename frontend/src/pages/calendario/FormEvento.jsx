import { useEffect, useState } from "react";
import { Alert, Button, Card, Col, Form, Row } from "react-bootstrap";
import { Link, useNavigate, useParams } from "react-router-dom";

import { buscarEvento, criarEvento, editarEvento } from "../../api/calendario";
import AlertaErro from "../../components/AlertaErro";
import Carregando from "../../components/Carregando";
import ErroCampo from "../../components/ErroCampo";
import { hojeISO } from "../../utils/formatacao";
import { ROTULOS } from "../../utils/rotulos";

// UC07: o local vem pré-preenchido com o último local usado (guardado neste navegador).
const CHAVE_ULTIMO_LOCAL = "pingpoli_ultimo_local";

function ultimoLocal() {
  try {
    return localStorage.getItem(CHAVE_ULTIMO_LOCAL) || "";
  } catch {
    return "";
  }
}

function lembrarLocal(local) {
  try {
    localStorage.setItem(CHAVE_ULTIMO_LOCAL, local);
  } catch {
    // sem localStorage o formulário funciona igual, só não pré-preenche
  }
}

// UC07 · Novo evento (/eventos/novo) e Editar evento (/eventos/:id/editar). Só o Diretor chega aqui (RotaDiretor).
export default function FormEvento() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState({
    tipo: "", titulo: "", data_evento: "", hora_inicio: "", hora_fim: "", local_evento: ultimoLocal(), descricao: "",
  });
  const [carregando, setCarregando] = useState(editando);
  const [erroCarga, setErroCarga] = useState(null);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  // UC07-a: formulário preenchido com os dados atuais
  useEffect(() => {
    if (!editando) return;
    buscarEvento(id)
      .then((e) => setForm({
        tipo: e.tipo, titulo: e.titulo, data_evento: e.data_evento, hora_inicio: e.hora_inicio,
        hora_fim: e.hora_fim, local_evento: e.local_evento, descricao: e.descricao,
      }))
      .catch(setErroCarga)
      .finally(() => setCarregando(false));
  }, [editando, id]);

  function alterar(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function salvar(e) {
    e.preventDefault();
    setErro(null);
    // Campo vazio não vai: a API responde "Este campo é obrigatório." em vez de "Formato inválido".
    const dados = {
      ...form,
      tipo: form.tipo || undefined,
      data_evento: form.data_evento || undefined,
      hora_inicio: form.hora_inicio || undefined,
      hora_fim: form.hora_fim || undefined,
      titulo: form.titulo.trim(),
      local_evento: form.local_evento.trim(),
      descricao: form.descricao.trim(),
    };
    setEnviando(true);
    try {
      const evento = editando ? await editarEvento(id, dados) : await criarEvento(dados);
      lembrarLocal(evento.local_evento);
      navigate(`/eventos/${evento.id}`, editando ? undefined : { state: { mensagem: "Evento criado" } });
    } catch (falha) {
      setErro(falha);
      setEnviando(false);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  if (carregando) return <Carregando />;
  if (erroCarga) return <AlertaErro erro={erroCarga.status === 404 ? "Evento não encontrado." : erroCarga} />;

  const erroGeral = erro && (erro.codigo || erro.status !== 400) ? erro : null;
  const invalido = (campo) => Boolean(erro?.campos?.[campo]);

  return (
    <Card>
      <Card.Body>
        <h1 className="h4 mb-3">{editando ? "Editar evento" : "Novo evento"}</h1>
        <AlertaErro erro={erroGeral} />
        {erro?.status === 400 && !erroGeral && <Alert variant="danger">Corrija os campos indicados.</Alert>}

        <Form noValidate onSubmit={salvar}>
          <Row>
            <Col sm={4}>
              <Form.Group className="mb-3" controlId="tipo">
                <Form.Label>Tipo</Form.Label>
                <Form.Select name="tipo" value={form.tipo} onChange={alterar} isInvalid={invalido("tipo")} required>
                  <option value="">Selecione…</option>
                  {Object.entries(ROTULOS.tipoEvento).map(([valor, nome]) => (
                    <option key={valor} value={valor}>{nome}</option>
                  ))}
                </Form.Select>
                <Form.Text muted>Campeonatos são cadastrados em Campeonatos.</Form.Text>
                <ErroCampo erro={erro} campo="tipo" />
              </Form.Group>
            </Col>
            <Col sm={8}>
              <Form.Group className="mb-3" controlId="titulo">
                <Form.Label>Título</Form.Label>
                <Form.Control name="titulo" value={form.titulo} onChange={alterar} maxLength={100}
                  isInvalid={invalido("titulo")} required />
                <ErroCampo erro={erro} campo="titulo" />
              </Form.Group>
            </Col>
          </Row>

          <Row>
            <Col sm={4}>
              <Form.Group className="mb-3" controlId="data_evento">
                <Form.Label>Data</Form.Label>
                <Form.Control type="date" name="data_evento" value={form.data_evento} onChange={alterar}
                  min={editando ? undefined : hojeISO()} isInvalid={invalido("data_evento")} required />
                <ErroCampo erro={erro} campo="data_evento" />
              </Form.Group>
            </Col>
            <Col xs={6} sm={4}>
              <Form.Group className="mb-3" controlId="hora_inicio">
                <Form.Label>Início</Form.Label>
                <Form.Control type="time" name="hora_inicio" value={form.hora_inicio} onChange={alterar}
                  isInvalid={invalido("hora_inicio")} required />
                <ErroCampo erro={erro} campo="hora_inicio" />
              </Form.Group>
            </Col>
            <Col xs={6} sm={4}>
              <Form.Group className="mb-3" controlId="hora_fim">
                <Form.Label>Término</Form.Label>
                <Form.Control type="time" name="hora_fim" value={form.hora_fim} onChange={alterar}
                  isInvalid={invalido("hora_fim")} required />
                <ErroCampo erro={erro} campo="hora_fim" />
              </Form.Group>
            </Col>
          </Row>

          <Form.Group className="mb-3" controlId="local_evento">
            <Form.Label>Local</Form.Label>
            <Form.Control name="local_evento" value={form.local_evento} onChange={alterar} maxLength={100}
              isInvalid={invalido("local_evento")} required />
            <ErroCampo erro={erro} campo="local_evento" />
          </Form.Group>

          <Form.Group className="mb-4" controlId="descricao">
            <Form.Label>Descrição (opcional)</Form.Label>
            <Form.Control as="textarea" rows={4} name="descricao" value={form.descricao} onChange={alterar}
              maxLength={1000} isInvalid={invalido("descricao")} />
            <Form.Text muted>{form.descricao.length}/1000</Form.Text>
            <ErroCampo erro={erro} campo="descricao" />
          </Form.Group>

          <div className="d-flex gap-2">
            <Button type="submit" disabled={enviando}>Salvar</Button>
            <Button as={Link} to={editando ? `/eventos/${id}` : "/calendario"} variant="outline-secondary">Cancelar</Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}
