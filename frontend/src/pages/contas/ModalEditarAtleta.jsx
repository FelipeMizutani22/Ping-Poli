import { useState } from "react";
import { Button, Col, Form, Modal, Row } from "react-bootstrap";

import { editarAtleta, listarCursos } from "../../api/contas";
import AlertaErro from "../../components/AlertaErro";
import ErroCampo from "../../components/ErroCampo";
import { useApi } from "../../hooks/useApi";
import { mascaraTelefone } from "../../utils/formatacao";

// UC03-b · O Diretor edita os dados de um membro (inclusive o e-mail). O NUSP não muda.
export default function ModalEditarAtleta({ atleta, onFechar, onSalvo }) {
  const { dados: cursos } = useApi(listarCursos);
  const [form, setForm] = useState({
    nome: atleta.nome,
    email: atleta.email,
    curso: String(atleta.curso.id),
    ano_ingresso: String(atleta.ano_ingresso),
    telefone: atleta.telefone || "",
  });
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);

  function alterar(e) {
    const { name, value } = e.target;
    setForm({ ...form, [name]: name === "telefone" ? mascaraTelefone(value) : value });
  }

  async function salvar(e) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      const atualizado = await editarAtleta(atleta.id, {
        ...form,
        nome: form.nome.trim(),
        email: form.email.trim(),
        curso: Number(form.curso),
        ano_ingresso: Number(form.ano_ingresso),
      });
      await onSalvo(atualizado);
    } catch (falha) {
      if (falha.status === 400) falha.message = "Corrija os campos destacados.";
      setErro(falha);
      setSalvando(false);
    }
  }

  const invalido = (campo) => Boolean(erro?.campos?.[campo]);

  return (
    <Modal show onHide={onFechar} centered size="lg">
      <Form noValidate onSubmit={salvar}>
        <Modal.Header closeButton>
          <Modal.Title className="h5">Editar dados · NUSP {atleta.nusp}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <AlertaErro erro={erro} />
          <Form.Group className="mb-3" controlId="editar-nome">
            <Form.Label>Nome completo</Form.Label>
            <Form.Control name="nome" maxLength={100} value={form.nome} onChange={alterar} isInvalid={invalido("nome")} />
            <ErroCampo erro={erro} campo="nome" />
          </Form.Group>
          <Form.Group className="mb-3" controlId="editar-email">
            <Form.Label>E-mail de acesso</Form.Label>
            <Form.Control type="email" name="email" maxLength={100} value={form.email} onChange={alterar}
              isInvalid={invalido("email")} />
            <Form.Text muted>Se mudar, o atleta passa a entrar com o e-mail novo e recebe um aviso nele.</Form.Text>
            <ErroCampo erro={erro} campo="email" />
          </Form.Group>
          <Row className="g-3">
            <Col sm={6}>
              <Form.Group controlId="editar-curso">
                <Form.Label>Curso</Form.Label>
                <Form.Select name="curso" value={form.curso} onChange={alterar} isInvalid={invalido("curso")}>
                  {(cursos || [atleta.curso]).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
                </Form.Select>
                <ErroCampo erro={erro} campo="curso" />
              </Form.Group>
            </Col>
            <Col sm={3}>
              <Form.Group controlId="editar-ano">
                <Form.Label>Ano de ingresso</Form.Label>
                <Form.Control type="number" name="ano_ingresso" min={1950} value={form.ano_ingresso}
                  onChange={alterar} isInvalid={invalido("ano_ingresso")} />
                <ErroCampo erro={erro} campo="ano_ingresso" />
              </Form.Group>
            </Col>
            <Col sm={3}>
              <Form.Group controlId="editar-telefone">
                <Form.Label>Telefone</Form.Label>
                <Form.Control name="telefone" inputMode="tel" value={form.telefone} onChange={alterar}
                  isInvalid={invalido("telefone")} />
                <ErroCampo erro={erro} campo="telefone" />
              </Form.Group>
            </Col>
          </Row>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={onFechar} disabled={salvando}>Cancelar</Button>
          <Button type="submit" disabled={salvando}>{salvando ? "Salvando..." : "Salvar"}</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}
