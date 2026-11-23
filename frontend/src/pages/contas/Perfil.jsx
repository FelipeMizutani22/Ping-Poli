import { useEffect, useState } from "react";
import { Alert, Button, Card, Col, Form, Row } from "react-bootstrap";

import { atualizarPerfil, buscarPerfil, listarCursos, trocarSenha } from "../../api/contas";
import AlertaErro from "../../components/AlertaErro";
import Carregando from "../../components/Carregando";
import ErroCampo from "../../components/ErroCampo";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { mascaraTelefone } from "../../utils/formatacao";
import { ROTULOS, rotulo } from "../../utils/rotulos";

const ANO_ATUAL = new Date().getFullYear();
const ANOS = Array.from({ length: 11 }, (_, i) => ANO_ATUAL - i);

// UC04 · Manter Perfil: dados pessoais (NUSP e e-mail somente leitura) e troca de senha.
export default function Perfil() {
  const { dados: perfil, carregando, erro } = useApi(buscarPerfil);

  if (carregando) return <Carregando />;
  if (erro) return <AlertaErro erro={erro} />;

  return (
    <Row className="g-4">
      <Col lg={7}><DadosPessoais perfil={perfil} /></Col>
      <Col lg={5}><TrocarSenha /></Col>
    </Row>
  );
}

function DadosPessoais({ perfil }) {
  const { recarregarUsuario } = useAuth();
  const { dados: cursos } = useApi(listarCursos);
  const [form, setForm] = useState(null);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);
  const [salvando, setSalvando] = useState(false);

  // Preenche o formulário com os dados atuais assim que eles chegam da API.
  useEffect(() => {
    setForm({
      nome: perfil.nome,
      curso: String(perfil.curso.id),
      ano_ingresso: String(perfil.ano_ingresso),
      telefone: perfil.telefone || "",
      mao_dominante: perfil.mao_dominante || "",
    });
  }, [perfil]);

  if (!form) return null;

  // O ano de ingresso antigo pode estar fora da janela de 10 anos: mantém na lista para não sumir.
  const anos = ANOS.includes(Number(form.ano_ingresso)) ? ANOS : [Number(form.ano_ingresso), ...ANOS];

  function alterar(e) {
    const { name, value } = e.target;
    setForm({ ...form, [name]: name === "telefone" ? mascaraTelefone(value) : value });
    setSucesso(false);
  }

  async function salvar(e) {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      await atualizarPerfil({
        ...form,
        nome: form.nome.trim(),
        curso: Number(form.curso),
        ano_ingresso: Number(form.ano_ingresso),
      });
      await recarregarUsuario(); // atualiza o nome que aparece na barra de navegação
      setSucesso(true);
    } catch (falha) {
      if (falha.status === 400) falha.message = "Corrija os campos destacados.";
      setErro(falha);
    } finally {
      setSalvando(false);
    }
  }

  const invalido = (campo) => Boolean(erro?.campos?.[campo]);

  return (
    <Card className="h-100">
      <Card.Header className="fw-semibold">Meus dados</Card.Header>
      <Card.Body>
        {sucesso && <Alert variant="success">Dados atualizados.</Alert>}
        <AlertaErro erro={erro} />

        <Form noValidate onSubmit={salvar}>
          <Row className="g-3 mb-3">
            <Col sm={7}>
              <Form.Group controlId="perfil-email">
                <Form.Label>E-mail</Form.Label>
                <Form.Control value={perfil.email} disabled readOnly />
              </Form.Group>
            </Col>
            <Col sm={5}>
              <Form.Group controlId="perfil-nusp">
                <Form.Label>NUSP</Form.Label>
                <Form.Control value={perfil.nusp} disabled readOnly />
              </Form.Group>
            </Col>
            <Col xs={12}>
              <Form.Text muted>
                E-mail e NUSP não podem ser alterados aqui. Se precisar, peça à Diretoria. · Perfil:{" "}
                {rotulo("papel", perfil.papel)}
              </Form.Text>
            </Col>
          </Row>

          <Form.Group className="mb-3" controlId="perfil-nome">
            <Form.Label>Nome completo</Form.Label>
            <Form.Control name="nome" maxLength={100} value={form.nome} onChange={alterar} isInvalid={invalido("nome")} />
            <ErroCampo erro={erro} campo="nome" />
          </Form.Group>

          <Row className="g-3 mb-3">
            <Col sm={7}>
              <Form.Group controlId="perfil-curso">
                <Form.Label>Curso</Form.Label>
                <Form.Select name="curso" value={form.curso} onChange={alterar} isInvalid={invalido("curso")}>
                  {(cursos || [perfil.curso]).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
                </Form.Select>
                <ErroCampo erro={erro} campo="curso" />
              </Form.Group>
            </Col>
            <Col sm={5}>
              <Form.Group controlId="perfil-ano">
                <Form.Label>Ano de ingresso</Form.Label>
                <Form.Select name="ano_ingresso" value={form.ano_ingresso} onChange={alterar}
                  isInvalid={invalido("ano_ingresso")}>
                  {anos.map((a) => <option key={a} value={a}>{a}</option>)}
                </Form.Select>
                <ErroCampo erro={erro} campo="ano_ingresso" />
              </Form.Group>
            </Col>
          </Row>

          <Row className="g-3 mb-4">
            <Col sm={7}>
              <Form.Group controlId="perfil-telefone">
                <Form.Label>Telefone / WhatsApp</Form.Label>
                <Form.Control name="telefone" inputMode="tel" placeholder="(11) 99999-9999" value={form.telefone}
                  onChange={alterar} isInvalid={invalido("telefone")} />
                <ErroCampo erro={erro} campo="telefone" />
              </Form.Group>
            </Col>
            <Col sm={5}>
              <Form.Group controlId="perfil-mao">
                <Form.Label>Mão dominante</Form.Label>
                <Form.Select name="mao_dominante" value={form.mao_dominante} onChange={alterar}>
                  <option value="">Não informar</option>
                  {Object.entries(ROTULOS.maoDominante).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                </Form.Select>
              </Form.Group>
            </Col>
          </Row>

          <div className="text-end">
            <Button type="submit" disabled={salvando}>{salvando ? "Salvando..." : "Salvar alterações"}</Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}

const SENHAS_VAZIAS = { senha_atual: "", nova_senha: "", confirmacao: "" };

function TrocarSenha() {
  const [form, setForm] = useState(SENHAS_VAZIAS);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);
  const [enviando, setEnviando] = useState(false);

  function alterar(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
    setSucesso(false);
  }

  async function enviar(e) {
    e.preventDefault();
    setErro(null);
    if (form.nova_senha !== form.confirmacao) {
      setErro({ message: "Corrija os campos destacados.", campos: { confirmacao: ["As senhas não conferem."] } });
      return;
    }
    setEnviando(true);
    try {
      await trocarSenha(form);
      setForm(SENHAS_VAZIAS);
      setSucesso(true);
    } catch (falha) {
      if (falha.status === 400) falha.message = "Corrija os campos destacados.";
      setErro(falha);
      setForm(SENHAS_VAZIAS); // por segurança, não deixa senhas preenchidas depois de um erro
    } finally {
      setEnviando(false);
    }
  }

  const invalido = (campo) => Boolean(erro?.campos?.[campo]);
  const incompleto = !form.senha_atual || !form.nova_senha || !form.confirmacao;

  return (
    <Card className="h-100">
      <Card.Header className="fw-semibold">Trocar senha</Card.Header>
      <Card.Body>
        {sucesso && <Alert variant="success">Senha alterada.</Alert>}
        <AlertaErro erro={erro} />
        <Form noValidate onSubmit={enviar}>
          <Form.Group className="mb-3" controlId="senha-atual">
            <Form.Label>Senha atual</Form.Label>
            <Form.Control type="password" name="senha_atual" autoComplete="current-password" maxLength={64}
              value={form.senha_atual} onChange={alterar} isInvalid={invalido("senha_atual")} />
            <ErroCampo erro={erro} campo="senha_atual" />
          </Form.Group>
          <Form.Group className="mb-3" controlId="senha-nova">
            <Form.Label>Nova senha</Form.Label>
            <Form.Control type="password" name="nova_senha" autoComplete="new-password" maxLength={64}
              value={form.nova_senha} onChange={alterar} isInvalid={invalido("nova_senha")} />
            <Form.Text muted>De 8 a 64 caracteres.</Form.Text>
            <ErroCampo erro={erro} campo="nova_senha" />
          </Form.Group>
          <Form.Group className="mb-4" controlId="senha-confirmacao">
            <Form.Label>Confirmar nova senha</Form.Label>
            <Form.Control type="password" name="confirmacao" autoComplete="new-password" maxLength={64}
              value={form.confirmacao} onChange={alterar} isInvalid={invalido("confirmacao")} />
            <ErroCampo erro={erro} campo="confirmacao" />
          </Form.Group>
          <div className="text-end">
            <Button type="submit" variant="outline-primary" disabled={enviando || incompleto}>
              {enviando ? "Alterando..." : "Alterar senha"}
            </Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}