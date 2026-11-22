import { Badge, Button, Card, Col, ListGroup, Row } from "react-bootstrap";
import { Link } from "react-router-dom";

import { buscarPainel } from "../../api/nucleo";
import AlertaErro from "../../components/AlertaErro";
import BadgeCategoriaAviso from "../../components/BadgeCategoriaAviso";
import Carregando from "../../components/Carregando";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData } from "../../utils/formatacao";
import { CORES_TIPO_CALENDARIO, rotulo } from "../../utils/rotulos";

// Página inicial (UC01 passo 9): T03 para o Atleta; T04 acrescenta o Painel Administrativo (UC01-c).
export default function Inicio() {
  const { usuario } = useAuth();
  const { dados: painel, carregando, erro } = useApi(buscarPainel);
  const primeiroNome = usuario?.nome?.split(" ")[0];

  return (
    <>
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <div>
          <h1 className="h3 mb-1">Olá, {primeiroNome}!</h1>
          <p className="text-muted mb-0">Veja o que está acontecendo na equipe.</p>
        </div>
        <div className="d-flex gap-2">
          <Button as={Link} to="/partidas/nova">Registrar partida</Button>
          <Button as={Link} to="/desempenho" variant="outline-primary">Meu desempenho</Button>
        </div>
      </div>

      {carregando && <Carregando />}
      <AlertaErro erro={erro} />

      {painel && (
        <>
          <Row className="g-3 mb-4">
            <Col md={painel.admin ? 4 : 6}>
              <CartaoContador
                titulo="Partidas aguardando sua confirmação"
                valor={painel.partidas_pendentes}
                destaque={painel.partidas_pendentes > 0}
                link="/partidas/pendentes"
                textoLink="Confirmar ou contestar"
              />
            </Col>
            <Col md={painel.admin ? 4 : 6}>
              <CartaoContador titulo="Notificações não lidas" valor={painel.notificacoes_nao_lidas} />
            </Col>
            {painel.admin && (
              <Col md={4}>
                <PainelAdministrativo admin={painel.admin} />
              </Col>
            )}
          </Row>

          <Row className="g-4">
            <Col lg={7}>
              <AvisosFixados avisos={painel.avisos_fixados} />
            </Col>
            <Col lg={5}>
              <ProximosEventos eventos={painel.proximos_eventos} />
            </Col>
          </Row>
        </>
      )}
    </>
  );
}

function CartaoContador({ titulo, valor, destaque = false, link, textoLink }) {
  return (
    <Card className={`h-100 ${destaque ? "destaque-amarelo" : ""}`}>
      <Card.Body>
        <div className="text-muted small">{titulo}</div>
        <div className="display-6 fw-bold">{valor}</div>
        {link && valor > 0 && <Link to={link} className="small">{textoLink} →</Link>}
      </Card.Body>
    </Card>
  );
}

function PainelAdministrativo({ admin }) {
  return (
    <Card className="h-100 border-primary">
      <Card.Header className="bg-primary text-white fw-semibold">Painel Administrativo</Card.Header>
      <ListGroup variant="flush">
        <ListGroup.Item action as={Link} to="/admin/atletas"
          className="d-flex justify-content-between align-items-center">
          Solicitações de cadastro
          <Badge bg={admin.solicitacoes_pendentes > 0 ? "warning" : "secondary"}
            text={admin.solicitacoes_pendentes > 0 ? "dark" : undefined}>
            {admin.solicitacoes_pendentes}
          </Badge>
        </ListGroup.Item>
        <ListGroup.Item action as={Link} to="/moderacao"
          className="d-flex justify-content-between align-items-center">
          Partidas contestadas
          <Badge bg={admin.partidas_contestadas > 0 ? "danger" : "secondary"}>{admin.partidas_contestadas}</Badge>
        </ListGroup.Item>
      </ListGroup>
    </Card>
  );
}

function AvisosFixados({ avisos }) {
  return (
    <Card className="h-100">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span className="fw-semibold">Avisos fixados</span>
        <Link to="/avisos" className="small">Ver todos</Link>
      </Card.Header>
      {avisos.length === 0 ? (
        <Card.Body className="text-muted">Nenhum aviso fixado no momento.</Card.Body>
      ) : (
        <ListGroup variant="flush">
          {avisos.map((aviso) => (
            <ListGroup.Item key={aviso.id} action as={Link} to={`/avisos/${aviso.id}`} className="destaque-amarelo">
              <div className="d-flex align-items-center gap-2 mb-1">
                <BadgeCategoriaAviso categoria={aviso.categoria} />
                <span className="fw-semibold">{aviso.titulo}</span>
                {!aviso.lido && <Badge bg="info">Novo</Badge>}
              </div>
              <div className="small text-muted text-truncate">{aviso.trecho}</div>
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
    </Card>
  );
}

function ProximosEventos({ eventos }) {
  return (
    <Card className="h-100">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span className="fw-semibold">Próximos eventos</span>
        <Link to="/calendario" className="small">Ver calendário</Link>
      </Card.Header>
      {eventos.length === 0 ? (
        <Card.Body className="text-muted">Nenhum evento nos próximos 30 dias.</Card.Body>
      ) : (
        <ListGroup variant="flush">
          {eventos.map((evento) => {
            const ehCampeonato = evento.tipo === "campeonato";
            const destino = ehCampeonato ? `/campeonatos/${evento.id}` : `/eventos/${evento.id}`;
            return (
              <ListGroup.Item key={`${evento.tipo}-${evento.id}`} action as={Link} to={destino}>
                <div className="d-flex align-items-center gap-2">
                  <Badge bg={CORES_TIPO_CALENDARIO[evento.tipo]} text={ehCampeonato ? "dark" : undefined}>
                    {rotulo("tipoCalendario", evento.tipo)}
                  </Badge>
                  <span className="fw-semibold">{evento.titulo}</span>
                  {evento.presente && <Badge bg="success">Presente</Badge>}
                </div>
                <div className="small text-muted">
                  {formatarData(evento.data)}
                  {ehCampeonato && evento.data_fim !== evento.data && ` a ${formatarData(evento.data_fim)}`}
                  {!ehCampeonato && ` · ${evento.hora_inicio}–${evento.hora_fim}`}
                  {evento.local && ` · ${evento.local}`}
                </div>
              </ListGroup.Item>
            );
          })}
        </ListGroup>
      )}
    </Card>
  );
}