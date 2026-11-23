import { useState } from "react";
import { Alert, Button, Card, Col, Form, Row } from "react-bootstrap";
import { Link, useNavigate } from "react-router-dom";

import { listarCursos, solicitarCadastro } from "../../api/contas";
import ErroCampo from "../../components/ErroCampo";
import { useApi } from "../../hooks/useApi";
import ModalConfirmacao from "./ModalConfirmacao";

const ANO_ATUAL = new Date().getFullYear();
const ANOS = Array.from({ length: 11 }, (_, i) => ANO_ATUAL - i); // ano atual − 10 até o ano atual (UC02)
const VAZIO = {
  nome: "", nusp: "", email: "", curso: "", ano_ingresso: "", telefone: "",
  senha: "", senha_confirmacao: "", aceite_termos: false,
};

import { mascaraTelefone } from "../../utils/formatacao";

// UC02 · Solicitar Cadastro (Visitante). A conta nasce Pendente e aguarda a aprovação da Diretoria.
export default function Cadastro() {
  const navigate = useNavigate();
  const { dados: cursos } = useApi(listarCursos);
  const [form, setForm] = useState(VAZIO);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [confirmarSaida, setConfirmarSaida] = useState(false);

  function alterar(e) {
    const { name, value, type, checked } = e.target;
    const valor = type === "checkbox" ? checked : name === "telefone" ? mascaraTelefone(value) : value;
    setForm({ ...form, [name]: valor });
  }

  // Erros que dá para ver antes de chamar a API (o backend confere tudo de novo).
  function validarLocalmente() {
    const campos = {};
    ["nome", "nusp", "email", "curso", "ano_ingresso", "senha", "senha_confirmacao"].forEach((c) => {
      if (!String(form[c]).trim()) campos[c] = ["Campo obrigatório."];
    });
    if (form.senha && form.senha_confirmacao && form.senha !== form.senha_confirmacao) {
      campos.senha_confirmacao = ["As senhas não conferem."];
    }
    if (!form.aceite_termos) campos.aceite_termos = ["É preciso aceitar os termos de uso e a política de privacidade."];
    return Object.keys(campos).length ? { campos, message: "Corrija os campos destacados." } : null;
  }

  async function enviar(e) {
    e.preventDefault();
    const problema = validarLocalmente();
    setErro(problema);
    if (problema) return;

    setEnviando(true);
    try {
      const resposta = await solicitarCadastro({
        ...form,
        nome: form.nome.trim(),
        email: form.email.trim(),
        nusp: Number(form.nusp),
        curso: Number(form.curso),
        ano_ingresso: Number(form.ano_ingresso),
      });
      const mensagem = resposta.aviso ? `${resposta.detail} ${resposta.aviso}` : resposta.detail;
      navigate("/login", { replace: true, state: { mensagem } });
    } catch (falha) {
      // 400 = erros por campo; 409 = e-mail/NUSP já usado (mensagem do UC02 f/g)
      if (falha.status === 400) falha.message = "Corrija os campos destacados.";
      if (falha.campos?.senha || falha.campos?.senha_confirmacao) {
        setForm((f) => ({ ...f, senha: "", senha_confirmacao: "" })); // UC02-e: limpa as senhas
      }
      setErro(falha);
    } finally {
      setEnviando(false);
    }
  }

  function cancelar() {
    const preenchido = Object.entries(form).some(([, v]) => v !== "" && v !== false);
    if (preenchido) setConfirmarSaida(true); // UC02-a: confirma o descarte
    else navigate("/login");
  }

  const invalido = (campo) => Boolean(erro?.campos?.[campo]);

  return (
    <div className="pagina-login d-flex align-items-center justify-content-center p-3">
      <Card style={{ maxWidth: 640, width: "100%" }} className="shadow my-4">
        <Card.Body className="p-4">
          <h1 className="h4 mb-1">Solicitar cadastro</h1>
          <p className="text-muted mb-4">
            Preencha seus dados. A Diretoria da equipe vai avaliar e você recebe a resposta por e-mail.
          </p>

          {erro && (
            <Alert variant={erro.status === 409 ? "warning" : "danger"}>
              {erro.message}
              {erro.codigo === "conta_existente" && <> <Link to="/login">Ir para o login</Link></>}
            </Alert>
          )}

          <Form noValidate onSubmit={enviar}>
            <Form.Group className="mb-3" controlId="nome">
              <Form.Label>Nome completo *</Form.Label>
              <Form.Control name="nome" maxLength={100} value={form.nome} onChange={alterar}
                isInvalid={invalido("nome")} autoFocus />
              <ErroCampo erro={erro} campo="nome" />
            </Form.Group>

            <Row className="g-3 mb-3">
              <Col sm={5}>
                <Form.Group controlId="nusp">
                  <Form.Label>NUSP *</Form.Label>
                  <Form.Control name="nusp" inputMode="numeric" maxLength={10} value={form.nusp}
                    onChange={(e) => alterar({ target: { name: "nusp", value: e.target.value.replace(/\D/g, "") } })}
                    isInvalid={invalido("nusp")} />
                  <ErroCampo erro={erro} campo="nusp" />
                </Form.Group>
              </Col>
              <Col sm={7}>
                <Form.Group controlId="email">
                  <Form.Label>E-mail *</Form.Label>
                  <Form.Control type="email" name="email" maxLength={100} placeholder="seu.email@exemplo.com"
                    value={form.email} onChange={alterar} isInvalid={invalido("email")} />
                  <Form.Text muted>Pode ser o @usp.br ou um e-mail pessoal (atletas formados).</Form.Text>
                  <ErroCampo erro={erro} campo="email" />
                </Form.Group>
              </Col>
            </Row>

            <Row className="g-3 mb-3">
              <Col sm={7}>
                <Form.Group controlId="curso">
                  <Form.Label>Curso *</Form.Label>
                  <Form.Select name="curso" value={form.curso} onChange={alterar} isInvalid={invalido("curso")}>
                    <option value="">Selecione…</option>
                    {(cursos || []).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
                  </Form.Select>
                  <ErroCampo erro={erro} campo="curso" />
                </Form.Group>
              </Col>
              <Col sm={5}>
                <Form.Group controlId="ano_ingresso">
                  <Form.Label>Ano de ingresso *</Form.Label>
                  <Form.Select name="ano_ingresso" value={form.ano_ingresso} onChange={alterar}
                    isInvalid={invalido("ano_ingresso")}>
                    <option value="">Selecione…</option>
                    {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
                  </Form.Select>
                  <ErroCampo erro={erro} campo="ano_ingresso" />
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3" controlId="telefone">
              <Form.Label>Telefone / WhatsApp</Form.Label>
              <Form.Control name="telefone" inputMode="tel" placeholder="(11) 99999-9999" value={form.telefone}
                onChange={alterar} isInvalid={invalido("telefone")} />
              <ErroCampo erro={erro} campo="telefone" />
            </Form.Group>

            <Row className="g-3 mb-3">
              <Col sm={6}>
                <Form.Group controlId="senha">
                  <Form.Label>Senha *</Form.Label>
                  <Form.Control type="password" name="senha" maxLength={64} autoComplete="new-password"
                    value={form.senha} onChange={alterar} isInvalid={invalido("senha")} />
                  <Form.Text muted>De 8 a 64 caracteres.</Form.Text>
                  <ErroCampo erro={erro} campo="senha" />
                </Form.Group>
              </Col>
              <Col sm={6}>
                <Form.Group controlId="senha_confirmacao">
                  <Form.Label>Confirmar senha *</Form.Label>
                  <Form.Control type="password" name="senha_confirmacao" maxLength={64} autoComplete="new-password"
                    value={form.senha_confirmacao} onChange={alterar} isInvalid={invalido("senha_confirmacao")} />
                  <ErroCampo erro={erro} campo="senha_confirmacao" />
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-4" controlId="aceite_termos">
              <Form.Check type="checkbox" name="aceite_termos" checked={form.aceite_termos} onChange={alterar}
                isInvalid={invalido("aceite_termos")}
                label="Li e aceito os termos de uso e a política de privacidade *" />
              <ErroCampo erro={erro} campo="aceite_termos" />
            </Form.Group>

            <div className="d-flex justify-content-end gap-2">
              <Button variant="outline-secondary" onClick={cancelar} disabled={enviando}>Cancelar</Button>
              <Button type="submit" disabled={enviando}>{enviando ? "Enviando..." : "Enviar solicitação"}</Button>
            </div>
          </Form>
        </Card.Body>
      </Card>

      {confirmarSaida && (
        <ModalConfirmacao
          titulo="Descartar o preenchimento?"
          texto="Os dados digitados serão perdidos."
          textoBotao="Descartar" variante="danger"
          onConfirmar={async () => navigate("/login")}
          onFechar={() => setConfirmarSaida(false)}
        />
      )}
    </div>
  );
}