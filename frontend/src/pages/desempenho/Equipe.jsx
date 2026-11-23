import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Col, Form, Row, Table } from 'react-bootstrap';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { buscarEquipe } from '../../api/desempenho';
import { listarCampeonatos } from '../../api/competicoes';
import Carregando from '../../components/Carregando';
import { formatarData, formatarMes, hojeISO } from '../../utils/formatacao';

const PADRAO = { periodo: '12m', competicao: 'todas', inicio: '', fim: '' };
const PERIODOS = { '3m': 'Últimos 3 meses', '6m': 'Últimos 6 meses', '12m': 'Últimos 12 meses', tudo: 'Todo o histórico' };

export default function Equipe() {
  const [form, setForm] = useState(PADRAO);
  const [aplicados, setAplicados] = useState(PADRAO);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [campeonatos, setCampeonatos] = useState([]);
  const [erroCampeonatos, setErroCampeonatos] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  const requisicao = useRef(0);

  async function carregar(filtros = PADRAO) {
    const numero = ++requisicao.current;
    setCarregando(true);
    setErro('');
    const params = { ...filtros };
    if (params.periodo !== 'custom') { delete params.inicio; delete params.fim; }
    try {
      const resposta = await buscarEquipe(params);
      if (numero !== requisicao.current) return;
      setDados(resposta);
      setAplicados({ ...filtros });
    } catch (falha) {
      if (numero !== requisicao.current) return;
      setErro(falha.status === 400 ? Object.values(falha.campos || {}).flat().join(' ') || falha.message : falha.message);
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
    carregar(form);
  }
  const mudar = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  const opcoes = new Map(campeonatos.map((c) => [String(c.id), c.nome]));
  return <div>
    <h1 className="h3 mb-3">Desempenho da equipe</h1>
    <Card className="mb-4"><Card.Body>
      <Form onSubmit={aplicar}>
        <fieldset disabled={carregando}>
          <Row className="g-3 align-items-end">
            <Col xs={12} md={6}><Form.Group controlId="equipe-periodo"><Form.Label>Período</Form.Label>
              <Form.Select name="periodo" value={form.periodo} onChange={mudar}>
                <option value="3m">Últimos 3 meses</option><option value="6m">Últimos 6 meses</option>
                <option value="12m">Últimos 12 meses</option><option value="tudo">Todo o histórico</option><option value="custom">Personalizado</option>
              </Form.Select></Form.Group></Col>
            <Col xs={12} md={6}><Form.Group controlId="equipe-competicao"><Form.Label>Competição</Form.Label>
              <Form.Select name="competicao" value={form.competicao} onChange={mudar}>
                <option value="todas">Todas</option><option value="amistoso">Amistoso/Treino</option>
                {[...opcoes].map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
              </Form.Select></Form.Group></Col>
            {form.periodo === 'custom' && <>
              <Col xs={12} sm={6}><Form.Group controlId="equipe-inicio"><Form.Label>Data inicial</Form.Label><Form.Control required type="date" name="inicio" value={form.inicio} max={hojeISO()} onChange={mudar} /></Form.Group></Col>
              <Col xs={12} sm={6}><Form.Group controlId="equipe-fim"><Form.Label>Data final</Form.Label><Form.Control required type="date" name="fim" value={form.fim} min={form.inicio} max={hojeISO()} onChange={mudar} /></Form.Group></Col>
            </>}
            <Col xs={12}><Button type="submit">Aplicar filtros</Button></Col>
          </Row>
        </fieldset>
      </Form>
      {erroCampeonatos && <Alert variant="warning" className="mt-3 mb-0">Não foi possível carregar a lista completa de campeonatos. Selecione Todas ou Amistoso/Treino, ou tente novamente quando a lista estiver disponível. <Button variant="link" size="sm" onClick={() => setTentativa(tentativa + 1)}>Tentar novamente</Button></Alert>}
    </Card.Body></Card>
    {erro && <Alert variant="danger" role="alert">{erro} {dados && 'Os resultados anteriores foram mantidos.'}<div><Button variant="outline-danger" size="sm" disabled={carregando} onClick={() => carregar(form)}>Tentar novamente</Button></div></Alert>}
    {carregando && <div role="status"><Carregando texto="Carregando equipe..." /></div>}
    {dados && !carregando && <>
      <p className="text-muted">{aplicados.periodo === 'custom' ? `${formatarData(aplicados.inicio)} a ${formatarData(aplicados.fim)}` : PERIODOS[aplicados.periodo]} · {aplicados.competicao === 'todas' ? 'Todas as competições' : aplicados.competicao === 'amistoso' ? 'Amistoso/Treino' : opcoes.get(aplicados.competicao)}</p>
      <Card className="mb-4"><Card.Body>
        <h2 className="h5">Ranking da equipe</h2>
        <p className="text-muted">Somente atletas com pelo menos 5 partidas confirmadas nos filtros aplicados. Ordem: percentual de vitórias, saldo de sets, partidas e nome.</p>
        {dados.ranking.length ? <Table responsive striped><thead><tr><th scope="col">Posição</th><th scope="col">Atleta</th><th scope="col">Partidas</th><th scope="col">Vitórias</th><th scope="col">Vitórias (%)</th><th scope="col">Saldo de sets</th></tr></thead>
          <tbody>{dados.ranking.map((item) => <tr key={item.atleta.id}><td>{item.posicao}º</td><th scope="row">{item.atleta.nome}</th><td>{item.partidas}</td><td>{item.vitorias}</td><td>{Number(item.pct_vitorias).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%</td><td>{item.saldo_sets > 0 ? '+' : ''}{item.saldo_sets}</td></tr>)}</tbody></Table>
          : <Alert variant="info" className="mb-0">Nenhum atleta tem 5 partidas confirmadas nos filtros aplicados.</Alert>}
      </Card.Body></Card>
      <Card><Card.Body><h2 className="h5">Partidas da equipe por mês</h2>
        <p className="text-muted">Cada partida é contada uma vez, mesmo quando os dois participantes são da Poli. Inclui jogos de atletas fora do ranking.</p>
        {!dados.partidas_por_mes.some((mes) => mes.partidas > 0) && <Alert variant="info">Nenhuma partida confirmada nos filtros aplicados.</Alert>}
        <div style={{ height: 300, minWidth: 0 }}><ResponsiveContainer width="100%" height="100%"><BarChart data={dados.partidas_por_mes} margin={{ right: 20, left: -15, bottom: 15 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="mes" tickFormatter={formatarMes} minTickGap={20} /><YAxis allowDecimals={false} /><Tooltip labelFormatter={formatarMes} /><Bar dataKey="partidas" name="Partidas" fill="#1d3f8f" /></BarChart></ResponsiveContainer></div>
      </Card.Body></Card>
    </>}
  </div>;
}
