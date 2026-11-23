import { useEffect, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, Modal, Row, Table } from 'react-bootstrap';
import { Link, useLocation, useParams } from 'react-router-dom';
import { buscarCampeonato, cancelarCampeonato, editarCampeonato } from '../../api/competicoes';
import BadgeStatus from '../../components/BadgeStatus';
import Carregando from '../../components/Carregando';
import { useAuth } from '../../contexts/AuthContext';
import { formatarData } from '../../utils/formatacao';
import { exibirHorario, linkSeguro, mensagensErro, valorInscricao } from '../../utils/competicoes';

export default function DetalheCampeonato() {
  const { id } = useParams();
  const { state } = useLocation();
  const { ehDiretor } = useAuth();
  const [campeonato, setCampeonato] = useState(null);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [tentativa, setTentativa] = useState(0);
  const [acao, setAcao] = useState(null);
  const [motivo, setMotivo] = useState('');
  const [erroAcao, setErroAcao] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [mensagem, setMensagem] = useState(state?.mensagem || '');
  useEffect(() => {
    let ativo = true;
    setCarregando(true); setErro(''); setAcao(null);
    buscarCampeonato(id).then((dados) => { if (ativo) setCampeonato(dados); })
      .catch((falha) => { if (ativo) setErro(falha.status === 404 ? 'Campeonato não encontrado.' : falha.message); })
      .finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [id, tentativa]);
  function abrir(tipo) { setAcao(tipo); setMotivo(''); setErroAcao(''); }
  async function confirmar(e) {
    e.preventDefault(); setEnviando(true); setErroAcao('');
    try {
      const dados = acao === 'cancelar' ? await cancelarCampeonato(id, motivo.trim())
        : await editarCampeonato(id, { status: acao === 'abrir' ? 'inscricoes_abertas' : 'inscricoes_encerradas' });
      setCampeonato(dados); setMensagem(acao === 'cancelar' ? 'Campeonato cancelado.' : 'Status das inscrições atualizado.'); setAcao(null);
    } catch (falha) { setErroAcao(falha.status === 400 ? mensagensErro(falha.campos).join(' ') : falha.message); }
    finally { setEnviando(false); }
  }
  const titulos = { abrir: 'Abrir inscrições agora', encerrar: 'Encerrar inscrições agora', cancelar: 'Cancelar campeonato' };
  if (carregando) return <Carregando texto="Carregando campeonato..." />;
  if (erro) return <><Alert variant="danger" role="alert">{erro}<div><Button variant="outline-danger" onClick={() => setTentativa(tentativa + 1)}>Tentar novamente</Button></div></Alert><Link to="/campeonatos">Voltar aos campeonatos</Link></>;
  const c = campeonato;
  const regulamento = linkSeguro(c.link_regulamento);
  return <div>
    <Link to="/campeonatos">← Campeonatos</Link>
    <div className="d-flex justify-content-between align-items-start flex-wrap gap-3 my-3">
      <div><h1 className="h3">{c.nome}</h1><BadgeStatus status={c.status} grupo="statusCampeonato" /> {c.inscrito && <Badge bg="primary">Você está inscrito</Badge>}</div>
      {ehDiretor && <div className="d-flex flex-wrap gap-2">
        <Button as={Link} to={`/campeonatos/${id}/editar`} variant="outline-primary">Editar campeonato</Button>
        {c.status === 'planejado' && <Button onClick={() => abrir('abrir')}>Abrir inscrições agora</Button>}
        {c.status === 'inscricoes_abertas' && <Button variant="outline-primary" onClick={() => abrir('encerrar')}>Encerrar inscrições agora</Button>}
        {!['finalizado', 'cancelado'].includes(c.status) && <Button variant="outline-danger" onClick={() => abrir('cancelar')}>Cancelar campeonato</Button>}
      </div>}
    </div>
    {mensagem && <Alert variant="success" dismissible onClose={() => setMensagem('')}>{mensagem}</Alert>}
    {c.status === 'cancelado' && <Alert variant="warning">Este campeonato foi cancelado. Os dados estão disponíveis para consulta do histórico.</Alert>}
    <Card className="mb-4"><Card.Body><Row className="g-3">
      <Col xs={12} md={6}><h2 className="h5">Informações</h2><dl className="mb-0">
        <dt>Organizador</dt><dd>{c.organizador}</dd><dt>Local</dt><dd>{c.local_campeonato}</dd>
        <dt>Datas</dt><dd>{formatarData(c.data_inicio)} a {formatarData(c.data_fim)}</dd>
        <dt>Valor da inscrição</dt><dd>{valorInscricao(c.valor_inscricao)}</dd>
      </dl></Col>
      <Col xs={12} md={6}><h2 className="h5">Inscrições</h2><dl>
        <dt>Abertura</dt><dd>{exibirHorario(c.abertura_inscricoes)} (Brasília)</dd>
        <dt>Encerramento</dt><dd>{exibirHorario(c.encerramento_inscricoes)} (Brasília)</dd>
      </dl>{regulamento ? <a href={regulamento} target="_blank" rel="noopener noreferrer">Consultar regulamento (nova aba)</a> : <p className="text-muted">Regulamento não disponibilizado.</p>}</Col>
    </Row>{c.observacoes && <><h2 className="h5 mt-3">Observações</h2><p className="mb-0" style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{c.observacoes}</p></>}</Card.Body></Card>
    <Card><Card.Body><h2 className="h5">Categorias</h2>
      {c.categorias.length ? <Table responsive striped className="mb-0"><thead><tr><th scope="col">Categoria</th><th scope="col">Total de vagas</th><th scope="col">Vagas restantes</th><th scope="col">Sua inscrição</th></tr></thead><tbody>
        {c.categorias.map((cat) => <tr key={cat.id}><th scope="row">{cat.nome}</th><td>{cat.vagas ?? 'Sem limite'}</td><td>{cat.vagas_restantes === null ? 'Sem limite' : cat.vagas_restantes === 0 ? <Badge bg="secondary">Esgotadas</Badge> : cat.vagas_restantes}</td><td>{cat.inscrito ? <Badge bg="success">Inscrito</Badge> : 'Não inscrito'}</td></tr>)}
      </tbody></Table> : <p>Nenhuma categoria cadastrada.</p>}
    </Card.Body></Card>
    <Modal show={Boolean(acao)} onHide={() => { if (!enviando) setAcao(null); }} backdrop={enviando ? 'static' : true} keyboard={!enviando}>
      <Form onSubmit={confirmar}><Modal.Header closeButton={!enviando}><Modal.Title>{titulos[acao]}</Modal.Title></Modal.Header>
        <Modal.Body>{erroAcao && <Alert variant="danger" role="alert">{erroAcao}</Alert>}
          {acao === 'cancelar' ? <><p>O campeonato será cancelado e os inscritos serão comunicados. O histórico será preservado.</p><Form.Group controlId="cancelamento-motivo"><Form.Label>Motivo</Form.Label><Form.Control as="textarea" rows={3} required minLength={10} maxLength={300} value={motivo} disabled={enviando} onChange={(e) => setMotivo(e.target.value)} /><Form.Text>De 10 a 300 caracteres.</Form.Text></Form.Group></>
            : <p>Confirma {acao === 'abrir' ? 'a abertura' : 'o encerramento'} das inscrições? A data correspondente será ajustada para agora.</p>}
        </Modal.Body><Modal.Footer><Button variant="outline-secondary" disabled={enviando} onClick={() => setAcao(null)}>Voltar</Button><Button type="submit" variant={acao === 'cancelar' ? 'danger' : 'primary'} disabled={enviando || (acao === 'cancelar' && motivo.trim().length < 10)}>{enviando ? 'Salvando...' : 'Confirmar'}</Button></Modal.Footer>
      </Form>
    </Modal>
  </div>;
}
