import { useState } from "react";
import { Alert, Badge, Button, Card, Col, Row } from "react-bootstrap";
import { Link, useLocation, useParams } from "react-router-dom";

import { buscarPartida, confirmarPartida } from "../../api/partidas";
import AlertaErro from "../../components/AlertaErro";
import BadgeStatus from "../../components/BadgeStatus";
import Carregando from "../../components/Carregando";
import PlacarSets from "../../components/PlacarSets";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData, formatarDataHora } from "../../utils/formatacao";
import { rotulo } from "../../utils/rotulos";
import ModalContestar from "./ModalContestar";

// Resumo da partida (UC15 passo 10) e, para o adversário, Confirmar / Contestar (UC16)
export default function DetalhePartida() {
  const { id } = useParams();
  const location = useLocation();
  const { usuario } = useAuth();
  const { dados: p, carregando, erro, recarregar } = useApi(() => buscarPartida(id), [id]);
  const [mensagem, setMensagem] = useState(location.state?.mensagem || null);
  const [erroAcao, setErroAcao] = useState(null);
  const [contestando, setContestando] = useState(false);
  const [enviando, setEnviando] = useState(false);

  if (carregando && !p) return <Carregando />;
  if (erro) return <AlertaErro erro={erro.status === 404 ? "Partida não encontrada." : erro} />;
  if (!p) return null;

  const souAdversario = p.adversario?.id === usuario.id;
  const podeResponder = souAdversario && p.status === "pendente";
  const nomeAdversario = p.adversario?.nome || p.adversario_externo?.nome;
  const vencedorNome = p.vencedor === "atleta" ? p.atleta.nome : nomeAdversario;

  async function confirmar() {
    setErroAcao(null);
    setEnviando(true);
    try {
      await confirmarPartida(p.id);
      setMensagem("Partida confirmada");
    } catch (falha) {
      setErroAcao(falha); // UC16-d: não está mais pendente → mostra a situação atual
    } finally {
      setEnviando(false);
      recarregar();
    }
  }

  return (
    <>
      {mensagem && <Alert variant="success" dismissible onClose={() => setMensagem(null)}>{mensagem}</Alert>}
      <AlertaErro erro={erroAcao} onFechar={() => setErroAcao(null)} />

      <Card>
        <Card.Body>
          <div className="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
            <div>
              <h1 className="h4 mb-1">{p.atleta.nome} × {nomeAdversario}</h1>
              <div className="text-muted">
                {formatarData(p.data_jogo)} · {p.competicao.nome}
                {p.categoria && ` · ${p.categoria.nome}`}{p.fase && ` · ${p.fase}`}
              </div>
            </div>
            <BadgeStatus status={p.status} />
          </div>

          <Row className="g-3 mb-3">
            <Col md={4}>
              <div className="text-muted small">Resultado</div>
              <div className="fs-4 fw-bold">{p.placar_sets.atleta}–{p.placar_sets.adversario}</div>
              <div>Vencedor: <strong>{vencedorNome}</strong></div>
            </Col>
            <Col md={8}>
              <div className="text-muted small">Placar set a set ({p.atleta.nome} primeiro)</div>
              <div className="fs-5"><PlacarSets sets={p.sets} /></div>
              <div className="small text-muted">
                {rotulo("formato", p.formato)} · {rotulo("tipoAdversario", p.tipo_adversario)}
                {p.adversario_externo?.clube && ` · ${p.adversario_externo.clube}`}
              </div>
            </Col>
          </Row>

          {p.observacoes && <p className="mb-3"><span className="text-muted">Observações:</span> {p.observacoes}</p>}

          <div className="small text-muted">
            Registrada em {formatarDataHora(p.data_registro)}
            {p.data_confirmacao && ` · confirmada em ${formatarDataHora(p.data_confirmacao)}`}
          </div>

          {p.status === "pendente" && (
            <Alert variant="warning" className="mt-3 mb-0">
              {souAdversario
                ? `Você tem ${p.dias_para_responder} ${p.dias_para_responder === 1 ? "dia" : "dias"} para confirmar ou contestar. Depois disso, a partida é confirmada automaticamente.`
                : `Aguardando a confirmação de ${nomeAdversario} (${p.dias_para_responder} dias restantes).`}
            </Alert>
          )}

          {p.contestacao && (
            <Card className="mt-3 border-danger">
              <Card.Body>
                <h2 className="h6">
                  Contestação de {p.contestacao.contestante.nome}{" "}
                  <small className="text-muted">em {formatarDataHora(p.contestacao.data_contestacao)}</small>
                </h2>
                <p className="mb-2">{p.contestacao.justificativa}</p>
                {p.contestacao.sets_propostos.length > 0 && (
                  <div className="small">Placar proposto: <PlacarSets sets={p.contestacao.sets_propostos} /></div>
                )}
                {p.contestacao.resolvida_por ? (
                  <div className="small mt-2">
                    <Badge bg="success" className="me-1">Resolvida</Badge>
                    por {p.contestacao.resolvida_por.nome}: {p.contestacao.motivo_decisao}
                  </div>
                ) : (
                  <div className="small mt-2 text-muted">Aguardando decisão da Diretoria.</div>
                )}
              </Card.Body>
            </Card>
          )}

          <div className="d-flex gap-2 mt-4">
            {podeResponder && (
              <>
                <Button variant="success" onClick={confirmar} disabled={enviando}>Confirmar</Button>
                <Button variant="outline-danger" onClick={() => setContestando(true)} disabled={enviando}>Contestar</Button>
              </>
            )}
            <Button as={Link} to={podeResponder ? "/partidas/pendentes" : "/partidas"} variant="outline-secondary">
              Voltar
            </Button>
          </div>
        </Card.Body>
      </Card>

      {podeResponder && (
        <ModalContestar partida={p} mostrar={contestando} onFechar={() => setContestando(false)}
          onContestada={() => { setContestando(false); setMensagem("Contestação enviada à Diretoria"); recarregar(); }} />
      )}
    </>
  );
}
