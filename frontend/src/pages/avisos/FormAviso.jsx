import { useEffect, useState } from "react";
import { Alert, Button, Card, Col, Form, Row } from "react-bootstrap";
import { Link, useNavigate, useParams } from "react-router-dom";

import { buscarAviso, editarAviso, publicarAviso } from "../../api/avisos";
import AlertaErro from "../../components/AlertaErro";
import Carregando from "../../components/Carregando";
import ErroCampo from "../../components/ErroCampo";
import { hojeISO } from "../../utils/formatacao";
import { ROTULOS } from "../../utils/rotulos";

const FORM_INICIAL = {
  titulo: "",
  conteudo: "",
  categoria: "",
  fixado: false,
  data_expiracao: "",
  notificar_email: false,
};

// UC05 · Novo aviso (/avisos/novo) e Editar aviso (/avisos/:id/editar). Só o Diretor chega aqui (RotaDiretor).
export default function FormAviso() {
  const { id } = useParams();
  const editando = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState(FORM_INICIAL);
  const [carregando, setCarregando] = useState(editando);
  const [erroCarga, setErroCarga] = useState(null);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  // UC05-a passo 2: formulário preenchido com os dados atuais.
  useEffect(() => {
    if (!editando) return;
    buscarAviso(id)
      .then((a) => setForm({
        titulo: a.titulo,
        conteudo: a.conteudo,
        categoria: a.categoria,
        fixado: a.fixado,
        data_expiracao: a.data_expiracao || "",
        notificar_email: false, // o e-mail só é reenviado se marcado nesta edição
      }))
      .catch(setErroCarga)
      .finally(() => setCarregando(false));
  }, [editando, id]);

  function alterar(e) {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === "checkbox" ? checked : value });
  }

  async function salvar(e) {
    e.preventDefault();
    setErro(null);
    const dados = {
      ...form,
      titulo: form.titulo.trim(),
      conteudo: form.conteudo.trim(),
      categoria: form.categoria || undefined, // vazio não vai: a API responde "Este campo é obrigatório."
      data_expiracao: form.data_expiracao || null,
    };
    setEnviando(true);
    try {
      if (editando) {
        await editarAviso(id, dados);
        navigate(`/avisos/${id}`);
      } else {
        const aviso = await publicarAviso(dados);
        navigate(`/avisos/${aviso.id}`, { state: { mensagem: "Aviso publicado" } });
      }
    } catch (falha) {
      setErro(falha);
      setEnviando(false);
      window.scrollTo({ top: 0, behavior: "smooth" }); // a mensagem geral fica no topo do formulário
    }
  }

  if (carregando) return <Carregando />;
  if (erroCarga) return <AlertaErro erro={erroCarga} />;

  // Erro geral (ex.: limite de 3 fixados) aparece no topo; erros de campo, embaixo de cada campo.
  const erroGeral = erro && (erro.codigo || erro.status !== 400) ? erro : null;
  const invalido = (campo) => Boolean(erro?.campos?.[campo]);

  return (
    <Card>
      <Card.Body>
        <h1 className="h4 mb-3">{editando ? "Editar aviso" : "Novo aviso"}</h1>
        <AlertaErro erro={erroGeral} />
        {erro?.status === 400 && !erroGeral && <Alert variant="danger">Corrija os campos indicados.</Alert>}

        <Form noValidate onSubmit={salvar}>
          <Form.Group className="mb-3" controlId="titulo">
            <Form.Label>Título</Form.Label>
            <Form.Control name="titulo" value={form.titulo} onChange={alterar} maxLength={100}
              isInvalid={invalido("titulo")} required />
            <ErroCampo erro={erro} campo="titulo" />
          </Form.Group>

          <Form.Group className="mb-3" controlId="conteudo">
            <Form.Label>Conteúdo</Form.Label>
            <Form.Control as="textarea" rows={8} name="conteudo" value={form.conteudo} onChange={alterar}
              maxLength={5000} isInvalid={invalido("conteudo")} required />
            <Form.Text muted>{form.conteudo.length}/5000</Form.Text>
            <ErroCampo erro={erro} campo="conteudo" />
          </Form.Group>

          <Row>
            <Col sm={6}>
              <Form.Group className="mb-3" controlId="categoria">
                <Form.Label>Categoria</Form.Label>
                <Form.Select name="categoria" value={form.categoria} onChange={alterar}
                  isInvalid={invalido("categoria")} required>
                  <option value="">Selecione…</option>
                  {Object.entries(ROTULOS.categoriaAviso).map(([valor, nome]) => (
                    <option key={valor} value={valor}>{nome}</option>
                  ))}
                </Form.Select>
                <ErroCampo erro={erro} campo="categoria" />
              </Form.Group>
            </Col>
            <Col sm={6}>
              <Form.Group className="mb-3" controlId="data_expiracao">
                <Form.Label>Data de expiração (opcional)</Form.Label>
                <Form.Control type="date" name="data_expiracao" value={form.data_expiracao} onChange={alterar}
                  min={hojeISO()} isInvalid={invalido("data_expiracao")} />
                <ErroCampo erro={erro} campo="data_expiracao" />
              </Form.Group>
            </Col>
          </Row>

          <Form.Check className="mb-2" type="checkbox" id="fixado" name="fixado" label="Fixar no topo"
            checked={form.fixado} onChange={alterar} />
          <Form.Check className="mb-4" type="checkbox" id="notificar_email" name="notificar_email"
            label="Notificar os atletas por e-mail" checked={form.notificar_email} onChange={alterar} />

          <div className="d-flex gap-2">
            <Button type="submit" disabled={enviando}>
              {editando ? "Salvar" : "Publicar"}
            </Button>
            <Button as={Link} to={editando ? `/avisos/${id}` : "/avisos"} variant="outline-secondary">
              Cancelar
            </Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}
