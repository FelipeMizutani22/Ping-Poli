import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Modal } from "react-bootstrap";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { alternarFixado, buscarAviso, excluirAviso } from "../../api/avisos";
import AlertaErro from "../../components/AlertaErro";
import BadgeCategoriaAviso from "../../components/BadgeCategoriaAviso";
import Carregando from "../../components/Carregando";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData, formatarDataHora } from "../../utils/formatacao";

// Aviso completo (UC06 passo 4). Abrir esta tela marca o aviso como lido na API (AvisoLeitura).
// O Diretor também edita, fixa/desafixa e exclui o aviso por aqui (UC05-a, b, c).
export default function DetalheAviso() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { ehDiretor } = useAuth();
  const { dados: aviso, carregando, erro, recarregar } = useApi(() => buscarAviso(id), [id]);
  const [erroAcao, setErroAcao] = useState(null);
  const [confirmandoExclusao, setConfirmandoExclusao] = useState(false);
  const [enviando, setEnviando] = useState(false);

  // UC06-d: aviso removido (ou expirado) enquanto era aberto → volta ao quadro com a mensagem da API.
  useEffect(() => {
    if (erro?.status === 404) navigate("/avisos", { replace: true, state: { mensagem: erro.message } });
  }, [erro, navigate]);

  if (carregando && !aviso) return <Carregando />;
  if (erro) return <AlertaErro erro={erro} />;
  if (!aviso) return null;

  // UC05-c: inverte fixado/não fixado. Com 3 fixados, a API devolve a mensagem do limite.
  async function fixar() {
    setErroAcao(null);
    setEnviando(true);
    try {
      await alternarFixado(aviso.id);
      await recarregar();
    } catch (falha) {
      setErroAcao(falha);
    } finally {
      setEnviando(false);
    }
  }

  // UC05-b: exclusão lógica, depois da confirmação.
  async function excluir() {
    setErroAcao(null);
    setEnviando(true);
    try {
      await excluirAviso(aviso.id);
      navigate("/avisos", { replace: true });
    } catch (falha) {
      setErroAcao(falha);
      setConfirmandoExclusao(false);
      setEnviando(false);
    }
  }

  return (
    <>
      {location.state?.mensagem && <Alert variant="success">{location.state.mensagem}</Alert>}
      <AlertaErro erro={erroAcao} onFechar={() => setErroAcao(null)} />

      <Card className={aviso.fixado ? "destaque-amarelo" : undefined}>
        <Card.Body>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <BadgeCategoriaAviso categoria={aviso.categoria} />
            {aviso.fixado && <Badge bg="light" text="dark">📌 Fixado</Badge>}
            {aviso.expirado && <Badge bg="secondary">Expirado</Badge>}
          </div>
          <h1 className="h4">{aviso.titulo}</h1>
          <p className="text-muted small mb-3">
            {aviso.autor.nome} · {formatarDataHora(aviso.data_publicacao)}
            {aviso.data_edicao && <> · editado em {formatarDataHora(aviso.data_edicao)}</>}
            {aviso.data_expiracao && <> · válido até {formatarData(aviso.data_expiracao)}</>}
          </p>
          <div style={{ whiteSpace: "pre-line" }}>{aviso.conteudo}</div>

          <div className="d-flex flex-wrap gap-2 mt-4">
            <Button as={Link} to="/avisos" variant="outline-primary">Voltar ao quadro</Button>
            {ehDiretor && (
              <>
                <Button as={Link} to={`/avisos/${aviso.id}/editar`} variant="primary">Editar</Button>
                <Button variant="outline-secondary" onClick={fixar} disabled={enviando}>
                  {aviso.fixado ? "Desafixar" : "📌 Fixar no topo"}
                </Button>
                <Button variant="outline-danger" onClick={() => setConfirmandoExclusao(true)} disabled={enviando}>
                  Excluir
                </Button>
              </>
            )}
          </div>
        </Card.Body>
      </Card>

      <Modal show={confirmandoExclusao} onHide={() => setConfirmandoExclusao(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title className="h5">Excluir aviso</Modal.Title>
        </Modal.Header>
        <Modal.Body>O aviso "{aviso.titulo}" será removido do quadro. Confirma a exclusão?</Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setConfirmandoExclusao(false)}>Cancelar</Button>
          <Button variant="danger" onClick={excluir} disabled={enviando}>Excluir</Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
