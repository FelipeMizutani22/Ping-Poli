import { useEffect, useState } from 'react';
import { Alert, Button, Card, Form, Modal, Table } from 'react-bootstrap';
import { Link, useParams } from 'react-router-dom';
import { incluirInscrito, listarInscritos, removerInscrito, salvarResultados } from '../../api/competicoes';
import BuscaAtleta from '../../components/BuscaAtleta';
import Carregando from '../../components/Carregando';
import { exibirHorario, mensagensErro } from '../../utils/competicoes';
import { csvInscritos } from '../../utils/exportarInscritos';
import './gestaoInscricoes.css';

const mensagemErro = e => e.status === 400 ? mensagensErro(e.campos).join(' ') : e.message;
export default function GestaoInscricoes() {
  const { id } = useParams();
  const [dados, setDados] = useState(null);
  const [campos, setCampos] = useState({});
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [tentativa, setTentativa] = useState(0);
  const [enviando, setEnviando] = useState(false);
  const [modal, setModal] = useState(null);
  const [erroModal, setErroModal] = useState('');
  const [atleta, setAtleta] = useState(null);
  const [categorias, setCategorias] = useState([]);
  const [observacoes, setObservacoes] = useState('');
  const [motivo, setMotivo] = useState('');
  function aplicar(d) {
    setDados(d);
    setCampos(Object.fromEntries(d.categorias.flatMap(c => c.inscricoes.map(i => [i.id, { colocacao: i.colocacao ?? '', destaque: i.destaque }]))));
  }
  useEffect(() => {
    let ativo = true; setCarregando(true); setErro('');
    listarInscritos(id).then(d => { if (ativo) aplicar(d); }).catch(e => { if (ativo) setErro(mensagemErro(e)); }).finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [id, tentativa]);
  function abrir(tipo, extra = {}) { setErroModal(''); setModal({ tipo, ...extra }); setAtleta(null); setCategorias([]); setObservacoes(''); setMotivo(''); }
  async function gravar(resultados, confirmar_empate = false) {
    setEnviando(true); setErro(''); setErroModal(''); setSucesso('');
    try {
      aplicar(await salvarResultados(id, { resultados, confirmar_empate })); setModal(null); setSucesso('Resultados registrados');
    } catch(e) {
      if (e.codigo === 'confirmar_empate') {
        const empates = e.campos.empates.map(p => `${dados.categorias.find(c => c.id === p.categoria)?.nome}: ${p.colocacao}º`).join('; ');
        setModal({ tipo: 'empate', resultados, empates });
      } else if (confirmar_empate) setErroModal(mensagemErro(e));
      else setErro(mensagemErro(e));
    } finally { setEnviando(false); }
  }
  function salvar(e) {
    e.preventDefault();
    const resultados = dados.categorias.flatMap(c => c.inscricoes).flatMap(i => {
      const valor = campos[i.id];
      const colocacao = valor.colocacao === '' ? null : Number(valor.colocacao);
      return colocacao === i.colocacao && valor.destaque === i.destaque ? [] : [{ id: i.id, colocacao, destaque: valor.destaque }];
    });
    if (!resultados.length) { setSucesso('Nenhuma alteração para salvar.'); return; }
    gravar(resultados);
  }
  async function confirmar(e) {
    e.preventDefault(); setEnviando(true); setErroModal(''); setSucesso('');
    try {
      if (modal.tipo === 'incluir') {
        aplicar(await incluirInscrito(id, { atleta: atleta.id, categorias, observacoes })); setSucesso('Inscrição incluída.');
      } else {
        await removerInscrito(modal.inscricao.id, motivo);
        setSucesso('Inscrição removida.');
        try { aplicar(await listarInscritos(id)); } catch { setErro('Inscrição removida, mas a lista não pôde ser atualizada. Recarregue a página.'); }
      }
      setModal(null);
    } catch(e) { setErroModal(mensagemErro(e)); } finally { setEnviando(false); }
  }
  function exportar() {
    const url = URL.createObjectURL(new Blob([csvInscritos(dados)], { type: 'text/csv;charset=utf-8;' }));
    const a = document.createElement('a'); a.href = url; a.download = `inscritos-campeonato-${id}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (carregando) return <Carregando />;
  if (!dados) return <Alert variant="danger">{erro}<Button onClick={() => setTentativa(tentativa + 1)}>Tentar novamente</Button></Alert>;
  const quantidade = dados.categorias.reduce((n, c) => n + c.inscricoes.length, 0);
  const alterado = dados.categorias.some(c => c.inscricoes.some(i => String(i.colocacao ?? '') !== String(campos[i.id]?.colocacao) || i.destaque !== campos[i.id]?.destaque));
  return <><div className="gestao-tela"><Link to={`/campeonatos/${id}`}>← Campeonato</Link><h1 className="h3 my-3">Inscritos e resultados — {dados.campeonato.nome}</h1>
    {erro && <Alert variant="danger" role="alert">{erro}</Alert>}{sucesso && <Alert variant="success" role="status">{sucesso}</Alert>}
    <div className="d-flex flex-wrap gap-2 mb-3"><Button disabled={enviando || alterado || dados.campeonato.status === 'cancelado'} onClick={() => abrir('incluir')}>Incluir inscrição</Button><Button variant="outline-primary" onClick={exportar}>Exportar CSV</Button><Button variant="outline-primary" onClick={() => window.print()}>Imprimir / salvar PDF</Button></div>
    {alterado && <p>Salve os resultados antes de incluir ou remover inscrições. A exportação utiliza os dados já salvos.</p>}
    {!dados.pode_registrar_resultados && <Alert variant="info">O registro de resultados só é permitido a partir da data de início de um campeonato não cancelado.</Alert>}
    {!quantidade && <Alert variant="info">Nenhuma inscrição neste campeonato</Alert>}
    <Form onSubmit={salvar}><fieldset disabled={enviando}>
      {dados.categorias.map(c => <Card key={c.id} className="mb-4"><Card.Body><h2 className="h5">{c.nome}</h2><p>{c.total_inscritos} inscrito(s) · Vagas restantes: {c.vagas_restantes ?? 'Sem limite'}</p>
        {c.inscricoes.length > 0 && <Table responsive striped><thead><tr><th>Atleta / NUSP</th><th>Curso</th><th>Inscrição</th><th>Observações</th><th>Colocação</th><th>Destaque</th><th>Ação</th></tr></thead><tbody>{c.inscricoes.map(i => <tr key={i.id}>
          <td>{i.atleta.nome}<br />{i.atleta.nusp}</td><td>{i.atleta.curso}</td><td>{exibirHorario(i.data_inscricao)}</td><td style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxWidth: 240 }}>{i.observacoes || '—'}</td>
          <td><Form.Control aria-label={`Colocação de ${i.atleta.nome} em ${c.nome}`} type="number" min={1} max={32767} step={1} style={{ minWidth: 90 }} disabled={!dados.pode_registrar_resultados} value={campos[i.id].colocacao} onChange={e => setCampos({ ...campos, [i.id]: { ...campos[i.id], colocacao: e.target.value } })} /></td>
          <td><Form.Control aria-label={`Destaque de ${i.atleta.nome} em ${c.nome}`} maxLength={50} style={{ minWidth: 150 }} disabled={!dados.pode_registrar_resultados} value={campos[i.id].destaque} onChange={e => setCampos({ ...campos, [i.id]: { ...campos[i.id], destaque: e.target.value } })} /></td>
          <td><Button variant="outline-danger" size="sm" disabled={alterado} onClick={() => abrir('remover', { inscricao: i })}>Remover</Button></td>
        </tr>)}</tbody></Table>}
      </Card.Body></Card>)}
      <Button type="submit" disabled={!dados.pode_registrar_resultados || !quantidade}>{enviando ? 'Salvando...' : 'Salvar resultados'}</Button>
    </fieldset></Form>
    <Modal show={!!modal} onHide={() => !enviando && setModal(null)} backdrop={enviando ? 'static' : true} keyboard={!enviando}>
      <Modal.Header closeButton={!enviando}><Modal.Title>{modal?.tipo === 'incluir' ? 'Incluir inscrição' : modal?.tipo === 'empate' ? 'Confirmar empates' : 'Remover inscrição'}</Modal.Title></Modal.Header>
      {modal?.tipo === 'empate' ? <><Modal.Body>{erroModal && <Alert variant="danger">{erroModal}</Alert>}Há colocações repetidas: {modal.empates}. Confirma que são empates?</Modal.Body><Modal.Footer><Button variant="secondary" disabled={enviando} onClick={() => setModal(null)}>Voltar e corrigir</Button><Button disabled={enviando} onClick={() => gravar(modal.resultados, true)}>Confirmar empates e salvar</Button></Modal.Footer></> : <Form onSubmit={confirmar}><Modal.Body>
        {erroModal && <Alert variant="danger" role="alert">{erroModal}</Alert>}
        <fieldset disabled={enviando}>{modal?.tipo === 'incluir' ? <><p>A inclusão pela diretoria pode ocorrer fora do prazo, respeitando as vagas.</p><BuscaAtleta valor={atleta} onSelect={setAtleta} />
          <div className="my-3">{dados.categorias.map(c => <Form.Check id={`manual-${c.id}`} key={c.id} label={`${c.nome} — ${c.vagas_restantes ?? 'sem limite de'} vagas`} disabled={c.vagas_restantes === 0} checked={categorias.includes(c.id)} onChange={e => setCategorias(e.target.checked ? [...categorias, c.id] : categorias.filter(v => v !== c.id))} />)}</div>
          <Form.Group controlId="manual-observacoes"><Form.Label>Observações</Form.Label><Form.Control as="textarea" maxLength={300} value={observacoes} onChange={e => setObservacoes(e.target.value)} /></Form.Group></> : <><p>Remover {modal?.inscricao.atleta.nome} de {modal?.inscricao.categoria.nome}? A vaga será liberada e o atleta receberá o motivo por e-mail.</p><Form.Group controlId="remover-motivo"><Form.Label>Motivo</Form.Label><Form.Control as="textarea" required minLength={10} maxLength={300} value={motivo} onChange={e => setMotivo(e.target.value)} /></Form.Group></>}
        </fieldset></Modal.Body><Modal.Footer><Button variant="secondary" disabled={enviando} onClick={() => setModal(null)}>Voltar</Button><Button type="submit" disabled={enviando || (modal?.tipo === 'incluir' ? !atleta || !categorias.length : motivo.trim().length < 10)}>{enviando ? 'Salvando...' : 'Confirmar'}</Button></Modal.Footer></Form>}
    </Modal></div>
    <div className="lista-impressao"><h1>{dados.campeonato.nome} — Inscritos</h1>{dados.categorias.map(c => <section key={c.id}><h2>{c.nome}</h2><p>{c.total_inscritos} inscrito(s) · Vagas restantes: {c.vagas_restantes ?? 'Sem limite'}</p><table><thead><tr><th>Nome / NUSP</th><th>Curso</th><th>Data</th><th>Observações</th><th>Colocação</th><th>Destaque</th></tr></thead><tbody>{c.inscricoes.map(i => <tr key={i.id}><td>{i.atleta.nome} / {i.atleta.nusp}</td><td>{i.atleta.curso}</td><td>{exibirHorario(i.data_inscricao)}</td><td>{i.observacoes}</td><td>{i.colocacao ?? '—'}</td><td>{i.destaque}</td></tr>)}</tbody></table></section>)}</div>
  </>;
}
