import { useState } from "react";
import { Alert, Button, Card, Form } from "react-bootstrap";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import Carregando from "../../components/Carregando";
import { useAuth } from "../../contexts/AuthContext";

// UC01 · Realizar Login (T01)
export default function Login() {
  const { usuario, carregando, entrar } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", senha: "" });
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  if (carregando) return <Carregando />;
  if (usuario) return <Navigate to="/" replace />; // UC01-d: já autenticado

  function alterar(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function enviar(e) {
    e.preventDefault();
    setErro(null);
    if (!form.email.trim() || !form.senha) {
      setErro({ message: "Preencha e-mail e senha", codigo: "campos_obrigatorios" }); // UC01-e
      return;
    }
    setEnviando(true);
    try {
      await entrar(form.email.trim(), form.senha);
      navigate(location.state?.de || "/", { replace: true });
    } catch (falha) {
      setErro(falha);
      if (falha.codigo === "credenciais_invalidas") setForm({ ...form, senha: "" }); // UC01-g
    } finally {
      setEnviando(false);
    }
  }

  const camposVazios = erro?.codigo === "campos_obrigatorios";

  return (
    <div className="pagina-login d-flex align-items-center justify-content-center p-3">
      <Card style={{ maxWidth: 420, width: "100%" }} className="shadow">
        <Card.Body className="p-4">
          <h1 className="h3 text-center mb-1">
            Ping<span style={{ color: "var(--pp-amarelo)" }}>Poli</span>
          </h1>
          <p className="text-center text-muted mb-4">Tênis de Mesa · Poli-USP</p>

          {erro && <Alert variant={erro.status === 403 ? "warning" : "danger"}>{erro.message}</Alert>}

          <Form noValidate onSubmit={enviar}>
            <Form.Group className="mb-3" controlId="email">
              <Form.Label>E-mail</Form.Label>
              <Form.Control
                type="email" name="email" maxLength={100} autoComplete="username" autoFocus
                value={form.email} onChange={alterar} isInvalid={camposVazios && !form.email.trim()}
              />
            </Form.Group>
            <Form.Group className="mb-4" controlId="senha">
              <Form.Label>Senha</Form.Label>
              <Form.Control
                type="password" name="senha" maxLength={64} autoComplete="current-password"
                value={form.senha} onChange={alterar} isInvalid={camposVazios && !form.senha}
              />
            </Form.Group>
            <Button type="submit" className="w-100" disabled={enviando}>
              {enviando ? "Entrando..." : "Entrar"}
            </Button>
          </Form>

          <div className="d-flex justify-content-between mt-3 small">
            <span className="text-muted" title="Em breve">Esqueci minha senha</span>
            <Link to="/cadastro">Solicitar cadastro</Link>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
}
