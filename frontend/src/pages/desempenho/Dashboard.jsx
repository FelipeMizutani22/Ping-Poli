import { useEffect, useRef, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, Row, Table, Tab, Tabs } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { buscarDesempenho } from '../../api/desempenho';
import { listarCampeonatos } from '../../api/competicoes';
import Equipe from './Equipe';
import BuscaAtleta from '../../components/BuscaAtleta';
import Carregando from '../../components/Carregando';
import { useAuth } from '../../contexts/AuthContext';
import { formatarData, formatarMes, hojeISO } from '../../utils/formatacao';

const PADRAO = { periodo: '12m', competicao: 'todas', tipo_adversario: 'todos', inicio: '', fim: '' };
const percentual = (valor) => `${Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;

function MeuDesempenho() {
  const { ehDiretor } = useAuth();
  const [form, setForm] = useState(PADRAO);
  const [atleta, setAtleta] = useState(null);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [campeonatos, setCampeonatos] = useState([]);
  const [conhecidos, setConhecidos] = useState({});
  const [erroCampeonatos, setErroCampeonatos] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  const requisicao = useRef(0);

  async function carregar(filtros = PADRAO, selecionado = null) {
    const numero = ++requisicao.current;
    setCarregando(true);
    setErro('');
    const params = { ...filtros, atleta: ehDiretor ? selecionado?.id : undefined };
    if (params.periodo !== 'custom') { delete params.inicio; delete params.fim; }
    try {
      const resposta = await buscarDesempenho(params);
      if (numero !== requisicao.current) return;
      setDados(resposta);
      setConhecidos((anteriores) => ({ ...anteriores, ...Object.fromEntries(resposta.por_competicao.filter((c) => c.campeonato_id !== null).map((c) => [String(c.campeonato_id), c.competicao])) }));
    } catch (falha) {
      if (numero !== requisicao.current) return;
      setErro(falha.status === 400 ? Object.values(falha.campos).flat().join(' ') : falha.message);
    } finally {
      if (numero === requisicao.current) setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    return () => { requisicao.current += 1; };
  }, []);

  useEffect(() => {
    let ativo = true;
    listarCampeonatos().then((lista) => {
      if (ativo) { setCampeonatos(lista); setErroCampeonatos(false); }
    }).catch(() => { if (ativo) setErroCampeonatos(true); });
    return () => { ativo = false; };
  }, [tentativa]);

  function aplicar(evento) {
    evento.preventDefault();
    if (form.periodo === 'custom' && (!form.inicio || !form.fim || form.inicio > form.fim || form.fim > hojeISO())) {
      setErro('Informe um período válido: a data final deve ser igual ou posterior à inicial e não pode estar no futuro.');
      return;
    }
    carregar(form, atleta);
  }

  const opcoes = new Map([...Object.entries(conhecidos), ...campeonatos.map((c) => [String(c.id), c.nome])]);
  for (const grupo of dados?.por_competicao || []) {
    if (grupo.campeonato_id !== null) opcoes.set(String(grupo.campeonato_id), grupo.competicao);
  }
  const mudar = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  const indicadores = dados?.indicadores;
  const sequencia = indicadores?.sequencia_atual;
  const cartoes = indicadores ? [
    ['Partidas', indicadores.partidas], ['Vitórias', indicadores.vitorias],
    ['Derrotas', indicadores.derrotas], ['Vitórias (%)', percentual(indicadores.pct_vitorias)],
    ['Saldo de sets', indicadores.saldo_sets > 0 ? `+${indicadores.saldo_sets}` : indicadores.saldo_sets],
    ['Sequência atual', sequencia ? `${sequencia.quantidade} ${sequencia.tipo === 'V' ? 'vitória(s)' : 'derrota(s)'}` : '—'],
  ] : [];

  return <div>
    <h1 className="h3 mb-3">Meu desempenho</h1><Link to="/confronto" className="ms-3">Confronto direto</Link>
    <Card className="mb-4"><Card.Body>
      <Form onSubmit={aplicar}>
        <fieldset disabled={carregando}>
          <Row className="g-3 align-items-end">
            <Col xs={12} md={4}><Form.Group controlId="desempenho-periodo"><Form.Label>Período</Form.Label>
              <Form.Select name="periodo" value={form.periodo} onChange={mudar}>
                <option value="3m">Últimos 3 meses</option><option value="6m">Últimos 6 meses</option>
                <option value="12m">Últimos 12 meses</option><option value="tudo">Todo o histórico</option><option value="custom">Personalizado</option>
              </Form.Select></Form.Group></Col>
            <Col xs={12} md={4}><Form.Group controlId="desempenho-competicao"><Form.Label>Competição</Form.Label>
              <Form.Select name="competicao" value={form.competicao} onChange={mudar}>
                <option value="todas">Todas</option><option value="amistoso">Amistoso/Treino</option>
                {[...opcoes].map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
              </Form.Select></Form.Group></Col>
            <Col xs={12} md={4}><Form.Group controlId="desempenho-tipo"><Form.Label>Tipo de adversário</Form.Label>
              <Form.Select name="tipo_adversario" value={form.tipo_adversario} onChange={mudar}>
                <option value="todos">Todos</option><option value="poli">Poli-USP</option><option value="externo">Externo</option>
              </Form.Select></Form.Group></Col>
            {form.periodo === 'custom' && <>
              <Col xs={12} sm={6}><Form.Group controlId="desempenho-inicio"><Form.Label>Data inicial</Form.Label><Form.Control required type="date" name="inicio" value={form.inicio} max={hojeISO()} onChange={mudar} /></Form.Group></Col>
              <Col xs={12} sm={6}><Form.Group controlId="desempenho-fim"><Form.Label>Data final</Form.Label><Form.Control required type="date" name="fim" value={form.fim} min={form.inicio} max={hojeISO()} onChange={mudar} /></Form.Group></Col>
            </>}
            {ehDiretor && <Col xs={12} md={8}><div className="mb-2">Atleta (sem seleção: meu desempenho)</div><BuscaAtleta valor={atleta} onSelect={setAtleta} incluirInativos /></Col>}
            <Col xs={12}><Button type="submit">Aplicar filtros</Button></Col>
          </Row>
        </fieldset>
      </Form>
      {erroCampeonatos && <Alert variant="warning" className="mt-3 mb-0">Não foi possível carregar a lista completa de campeonatos. As opções disponíveis vêm dos resultados consultados. <Button variant="link" size="sm" onClick={() => setTentativa(tentativa + 1)}>Tentar novamente</Button></Alert>}
    </Card.Body></Card>
    {erro && <Alert variant="danger" role="alert">{erro} {dados && 'Os resultados anteriores foram mantidos.'}<div><Button variant="outline-danger" size="sm" onClick={() => carregar(form, atleta)} disabled={carregando}>Tentar novamente</Button></div></Alert>}
    {carregando && <div role="status"><Carregando texto="Carregando desempenho..." /></div>}
    {dados && !carregando && <>
      <h2 className="h5">{dados.atleta.nome}</h2>
      <p className="text-muted">Resultados de {formatarData(dados.filtros.inicio)} a {formatarData(dados.filtros.fim)} · {dados.filtros.competicao === 'todas' ? 'Todas as competições' : dados.filtros.competicao === 'amistoso' ? 'Amistoso/Treino' : opcoes.get(String(dados.filtros.competicao)) || 'Campeonato selecionado'} · {({ todos: 'Todos os adversários', poli: 'Poli-USP', externo: 'Externos' })[dados.filtros.tipo_adversario]}</p>
      {!indicadores.partidas && <Alert variant="info">Nenhuma partida confirmada neste período. <Link to="/partidas/nova">Registrar partida</Link></Alert>}
      <Row className="g-3 mb-4">{cartoes.map(([titulo, valor]) => <Col xs={6} lg={2} key={titulo}><Card className="h-100"><Card.Body><div className="text-muted small">{titulo}</div><div className="h4 mt-2 mb-0">{valor}</div></Card.Body></Card></Col>)}</Row>
      <Row className="g-4 mb-4">
        <Col xs={12} lg={6}><Card className="h-100"><Card.Body><h2 className="h5">Evolução mensal</h2><p className="small text-muted">Meses sem partidas aparecem como lacunas.</p>
          <div style={{ height: 280, minWidth: 0 }}><ResponsiveContainer width="100%" height="100%"><LineChart data={dados.evolucao_mensal} margin={{ right: 20, left: -15, bottom: 10 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="mes" tickFormatter={formatarMes} minTickGap={20} /><YAxis domain={[0, 100]} unit="%" /><Tooltip labelFormatter={formatarMes} formatter={(v) => [percentual(v), 'Vitórias']} /><Line type="linear" dataKey="pct_vitorias" name="Vitórias (%)" stroke="#1d3f8f" strokeWidth={3} connectNulls={false} dot={{ r: 4 }} /></LineChart></ResponsiveContainer></div>
        </Card.Body></Card></Col>
        <Col xs={12} lg={6}><Card className="h-100"><Card.Body><h2 className="h5">Resultados por competição</h2>
          {dados.por_competicao.length ? <div style={{ height: 310, minWidth: 0 }}><ResponsiveContainer width="100%" height="100%"><BarChart data={dados.por_competicao} margin={{ right: 15, left: -15, bottom: 20 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="competicao" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="vitorias" name="Vitórias" fill="#1d3f8f" /><Bar dataKey="derrotas" name="Derrotas" fill="#6c757d" /></BarChart></ResponsiveContainer></div> : <p className="text-muted py-5">Nenhum resultado para exibir.</p>}
        </Card.Body></Card></Col>
      </Row>
      <Card className="mb-4"><Card.Body><h2 className="h5">Colocações em campeonatos</h2>
        {dados.colocacoes.length ? <Table responsive striped><thead><tr><th>Campeonato</th><th>Categoria</th><th>Colocação</th><th>Destaque</th><th>Data</th></tr></thead><tbody>{dados.colocacoes.map((c, i) => <tr key={i}><td>{c.campeonato}</td><td>{c.categoria}</td><td>{c.colocacao}º</td><td>{c.destaque || '—'}</td><td>{formatarData(c.data)}</td></tr>)}</tbody></Table> : <p className="text-muted mb-0">Nenhuma colocação neste período.</p>}
      </Card.Body></Card>
      <Card className="mb-4"><Card.Body><h2 className="h5">Partidas recentes</h2>
        {dados.recentes.length ? <Table responsive striped><thead><tr><th>Data</th><th>Competição</th><th>Adversário</th><th>Placar</th><th>Resultado</th></tr></thead><tbody>{dados.recentes.map((p) => <tr key={p.partida_id}><td>{formatarData(p.data)}</td><td>{p.competicao}</td><td>{p.adversario.nome}</td><td><Link to={`/partidas/${p.partida_id}`}>{p.placar}</Link></td><td><Badge bg={p.venceu ? 'success' : 'secondary'}>{p.venceu ? 'Vitória' : 'Derrota'}</Badge></td></tr>)}</tbody></Table> : <p className="text-muted mb-0">Nenhuma partida para exibir.</p>}
      </Card.Body></Card>
      <Card><Card.Body><h2 className="h5">Adversários mais enfrentados</h2>
        {dados.mais_enfrentados.length ? <Table responsive striped><thead><tr><th>Adversário</th><th>Partidas</th><th>Vitórias</th><th>Derrotas</th></tr></thead><tbody>{dados.mais_enfrentados.map((item) => <tr key={`${item.adversario.tipo}-${item.adversario.id}`}><td>{item.adversario.tipo === 'poli' ? <Link to={`/confronto?a=${dados.atleta.id}&b=${item.adversario.id}`}>{item.adversario.nome}</Link> : item.adversario.nome}</td><td>{item.partidas}</td><td>{item.vitorias}</td><td>{item.derrotas}</td></tr>)}</tbody></Table> : <p className="text-muted mb-0">Nenhum adversário para exibir.</p>}
      </Card.Body></Card>
    </>}
  </div>;
}


export default function Dashboard() {
  const { ehDiretor } = useAuth();
  if (!ehDiretor) return <MeuDesempenho />;
  return <Tabs defaultActiveKey="individual" className="mb-4" mountOnEnter unmountOnExit>
    <Tab eventKey="individual" title="Meu desempenho"><MeuDesempenho /></Tab>
    <Tab eventKey="equipe" title="Equipe"><Equipe /></Tab>
  </Tabs>;
}
