import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Col, Form, Row, Table } from 'react-bootstrap';
import { Link, useSearchParams } from 'react-router-dom';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { buscarConfronto } from '../../api/desempenho';
import BuscaAtleta from '../../components/BuscaAtleta';
import PlacarSets from '../../components/PlacarSets';
import { useAuth } from '../../contexts/AuthContext';
import { formatarData } from '../../utils/formatacao';
import { mensagensErro } from '../../utils/competicoes';

const campos = [['partidas', 'Partidas'], ['vitorias', 'Vitórias'], ['derrotas', 'Derrotas'], ['pct_vitorias', 'Vitórias (%)'], ['sets_pro', 'Sets ganhos'], ['sets_contra', 'Sets perdidos'], ['saldo_sets', 'Saldo de sets'], ['pontos_pro', 'Pontos ganhos'], ['pontos_contra', 'Pontos perdidos']];
const sequencia = s => s ? `${s.quantidade} ${s.tipo === 'V' ? 'vitória(s)' : 'derrota(s)'}` : 'Sem partidas';

export default function Confronto() {
  const { usuario, ehDiretor } = useAuth();
  const [params] = useSearchParams();
  const [a, setA] = useState(usuario);
  const [b, setB] = useState(null);
  const [periodo, setPeriodo] = useState('tudo');
  const [inicio, setInicio] = useState('');
  const [fim, setFim] = useState('');
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [aplicado, setAplicado] = useState('');
  const [ultimaConsulta, setUltimaConsulta] = useState(null);
  const pedido = useRef(0);
  async function consultar(filtros, rotulo) {
    const numero = ++pedido.current;
    setCarregando(true); setErro(''); setUltimaConsulta({ filtros, rotulo });
    try {
      const resultado = await buscarConfronto(filtros);
      if (numero !== pedido.current) return;
      setDados(resultado); setA(resultado.a); setB(resultado.b); setAplicado(rotulo);
    } catch (falha) {
      if (numero === pedido.current) setErro(falha.status === 400 ? mensagensErro(falha.campos).join(' ') : falha.status === 404 ? 'Atleta não encontrado.' : 'Serviço indisponível. Tente novamente em instantes');
    } finally { if (numero === pedido.current) setCarregando(false); }
  }
  const queryA = params.get('a');
  const queryB = params.get('b');
  useEffect(() => {
    if (queryB) consultar({ a: ehDiretor ? queryA || usuario.id : usuario.id, b: queryB, periodo: 'tudo' }, 'Todo o histórico');
    return () => { pedido.current += 1; };
  }, [queryA, queryB, ehDiretor, usuario.id]);
  function comparar(e) {
    e.preventDefault();
    if (!b) { setErro('Selecione um atleta para comparar'); return; }
    if (!a) { setErro('Selecione o atleta A'); return; }
    if (a.id === b.id) { setErro('Escolha um atleta diferente'); return; }
    consultar({ a: ehDiretor ? a.id : usuario.id, b: b.id, periodo, ...(periodo === 'custom' ? { inicio, fim } : {}) }, periodo === 'tudo' ? 'Todo o histórico' : `${formatarData(inicio)} a ${formatarData(fim)}`);
  }
  function destaque(titulo, partida) {
    return <Col xs={12} md={4}><Card className="h-100"><Card.Body><h3 className="h6">{titulo}</h3>{partida ? <><Link to={`/partidas/${partida.partida_id}`}>{formatarData(partida.data)} · {partida.placar}</Link><p className="mb-0">Vencedor: {partida.venceu ? dados.a.nome : dados.b.nome}</p></> : <p className="mb-0">Nenhuma partida.</p>}</Card.Body></Card></Col>;
  }
  return <div><Link to="/desempenho">← Desempenho</Link><h1 className="h3 my-3">Confronto direto</h1>
    <Card className="mb-4"><Card.Body><Form onSubmit={comparar}><fieldset disabled={carregando}><Row className="g-3">
      <Col xs={12} md={6}><div className="mb-2">Atleta A</div>{ehDiretor ? <BuscaAtleta valor={a} onSelect={setA} incluirInativos /> : <Form.Control aria-label="Atleta A" readOnly value={`${usuario.nome} · NUSP ${usuario.nusp}`} />}</Col>
      <Col xs={12} md={6}><div className="mb-2">Atleta B</div><BuscaAtleta valor={b} onSelect={setB} incluirInativos /></Col>
      <Col xs={12} md={4}><Form.Group controlId="confronto-periodo"><Form.Label>Período</Form.Label><Form.Select value={periodo} onChange={e => setPeriodo(e.target.value)}><option value="tudo">Todo o histórico</option><option value="custom">Personalizado</option></Form.Select></Form.Group></Col>
      {periodo === 'custom' && <><Col xs={12} md={4}><Form.Group controlId="confronto-inicio"><Form.Label>Data inicial</Form.Label><Form.Control type="date" required value={inicio} onChange={e => setInicio(e.target.value)} /></Form.Group></Col><Col xs={12} md={4}><Form.Group controlId="confronto-fim"><Form.Label>Data final</Form.Label><Form.Control type="date" required min={inicio || undefined} value={fim} onChange={e => setFim(e.target.value)} /></Form.Group></Col></>}
    </Row><Button type="submit" className="mt-3">{carregando ? 'Comparando...' : 'Comparar'}</Button></fieldset></Form></Card.Body></Card>
    {erro && <Alert variant="danger" role="alert">{erro}{ultimaConsulta && <div><Button variant="outline-danger" disabled={carregando} onClick={() => consultar(ultimaConsulta.filtros, ultimaConsulta.rotulo)}>Tentar novamente</Button></div>}</Alert>}
    {carregando && <p role="status">Carregando comparação...</p>}
    {dados && <section aria-busy={carregando}><h2 className="h4">{dados.a.nome} × {dados.b.nome}</h2><p className="text-muted">{aplicado}. Placares na perspectiva de {dados.a.nome}.</p>
      {erro && <p>Os resultados abaixo são da última consulta concluída.</p>}
      <p>Partidas aguardando confirmação no período: <strong>{dados.pendentes_entre_eles}</strong>. Não entram nos cálculos.</p>
      {!dados.partidas.length ? <Alert variant="info">Estes atletas ainda não se enfrentaram em partidas confirmadas</Alert> : <>
        <Card className="mb-4"><Card.Body><h3 className="h5">Retrospecto</h3><Table responsive><thead><tr><th>Indicador</th><th>{dados.a.nome}</th><th>{dados.b.nome}</th></tr></thead><tbody>{[['Vitórias', 'vitorias'], ['Sets', 'sets'], ['Pontos', 'pontos'], ['Vitórias (%)', 'pct']].map(([nome, chave]) => <tr key={chave}><th scope="row">{nome}</th><td>{dados.retrospecto[`${chave}_a`]}</td><td>{dados.retrospecto[`${chave}_b`]}</td></tr>)}</tbody></Table></Card.Body></Card>
        <Row className="g-3 mb-4">{destaque('Última partida', dados.ultima_partida)}{destaque(`Maior vitória de ${dados.a.nome}`, dados.maior_vitoria_a)}{destaque(`Maior vitória de ${dados.b.nome}`, dados.maior_vitoria_b)}</Row>
        <Card className="mb-4"><Card.Body><h3 className="h5">Vitórias acumuladas</h3><ResponsiveContainer width="100%" height={300}><LineChart data={dados.acumulado}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="data" tickFormatter={formatarData} /><YAxis allowDecimals={false} /><Tooltip labelFormatter={formatarData} /><Legend /><Line dataKey="vitorias_a" name={dados.a.nome} stroke="#303f86" /><Line dataKey="vitorias_b" name={dados.b.nome} stroke="#a06400" /></LineChart></ResponsiveContainer></Card.Body></Card>
        <Card className="mb-4"><Card.Body><h3 className="h5">Partidas em ordem cronológica</h3><Table striped responsive><thead><tr><th>Data</th><th>Competição</th><th>Placar</th><th>Set a set</th><th>Vencedor</th></tr></thead><tbody>{dados.partidas.map(p => <tr key={p.partida_id}><td>{formatarData(p.data)}</td><td>{p.competicao}</td><td><Link to={`/partidas/${p.partida_id}`}>{p.placar}</Link></td><td><PlacarSets sets={p.sets} /></td><td>{p.venceu ? dados.a.nome : dados.b.nome}</td></tr>)}</tbody></Table></Card.Body></Card>
      </>}
      <Card><Card.Body><h3 className="h5">Indicadores gerais no período</h3><p>Incluem partidas confirmadas contra todos os adversários, inclusive externos.</p><Table responsive striped><thead><tr><th>Indicador</th><th>{dados.a.nome}</th><th>{dados.b.nome}</th></tr></thead><tbody>{campos.map(([chave, nome]) => <tr key={chave}><th scope="row">{nome}</th><td>{dados.indicadores_a[chave]}</td><td>{dados.indicadores_b[chave]}</td></tr>)}<tr><th scope="row">Sequência atual</th><td>{sequencia(dados.indicadores_a.sequencia_atual)}</td><td>{sequencia(dados.indicadores_b.sequencia_atual)}</td></tr></tbody></Table></Card.Body></Card>
    </section>}
  </div>;
}
