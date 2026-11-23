import { useEffect, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, Row } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { listarCampeonatos } from '../../api/competicoes';
import BadgeStatus from '../../components/BadgeStatus';
import Carregando from '../../components/Carregando';
import { useAuth } from '../../contexts/AuthContext';
import { formatarData } from '../../utils/formatacao';
import { exibirHorario } from '../../utils/competicoes';
import { ROTULOS } from '../../utils/rotulos';

export default function ListaCampeonatos() {
  const { ehDiretor } = useAuth();
  const [status, setStatus] = useState('');
  const [lista, setLista] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    let ativo = true;
    setCarregando(true); setErro(null);
    listarCampeonatos({ status }).then((dados) => { if (ativo) setLista(dados); })
      .catch((falha) => { if (ativo) setErro(falha); })
      .finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [status, tentativa]);
  return <div>
    <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
      <h1 className="h3 mb-0">Campeonatos</h1>
      {ehDiretor && <Button as={Link} to="/campeonatos/novo">Novo campeonato</Button>}
    </div>
    <Form.Group controlId="campeonatos-status" className="mb-4" style={{ maxWidth: 360 }}>
      <Form.Label>Status</Form.Label><Form.Select value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="">Todos</option>{Object.entries(ROTULOS.statusCampeonato).map(([valor, nome]) => <option key={valor} value={valor}>{nome}</option>)}
      </Form.Select>
    </Form.Group>
    {carregando ? <Carregando texto="Carregando campeonatos..." /> : erro ? <Alert variant="danger" role="alert">{erro.message}<div><Button variant="outline-danger" onClick={() => setTentativa(tentativa + 1)}>Tentar novamente</Button></div></Alert>
      : !lista.length ? <Alert variant="info">{status ? 'Nenhum campeonato com este status.' : 'Nenhum campeonato disponível.'}</Alert>
      : <Row className="g-3">{lista.map((c) => <Col xs={12} lg={6} key={c.id}><Card className={`h-100 ${c.inscrito ? 'border-primary' : ''}`}><Card.Body>
        <div className="d-flex flex-wrap gap-2 mb-2"><BadgeStatus status={c.status} grupo="statusCampeonato" />{c.inscrito && <Badge bg="primary">Você está inscrito</Badge>}</div>
        <h2 className="h5"><Link to={`/campeonatos/${c.id}`}>{c.nome}</Link></h2>
        <p className="mb-1">{formatarData(c.data_inicio)} a {formatarData(c.data_fim)}</p>
        <p className="text-muted mb-2">{c.local_campeonato}</p>
        <p className="small">Prazo de inscrição: {exibirHorario(c.encerramento_inscricoes)} (Brasília)</p>
        <Button as={Link} to={`/campeonatos/${c.id}`} variant="outline-primary">Ver detalhes</Button>
      </Card.Body></Card></Col>)}</Row>}
  </div>;
}
