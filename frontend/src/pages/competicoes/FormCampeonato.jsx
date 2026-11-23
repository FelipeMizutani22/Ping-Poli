import { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Form, Modal, Row } from 'react-bootstrap';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { buscarCampeonato, criarCampeonato, editarCampeonato } from '../../api/competicoes';
import Carregando from '../../components/Carregando';
import { horarioBrasilia, mensagensErro, prepararCampeonato } from '../../utils/competicoes';

const novaCategoria = () => ({ chave: crypto.randomUUID(), nome: '', vagas: '' });
const inicial = () => ({ nome: '', organizador: '', local_campeonato: '', data_inicio: '', data_fim: '',
  abertura_inscricoes: '', encerramento_inscricoes: '', valor_inscricao: '', link_regulamento: '', observacoes: '', anunciar: true, categorias: [novaCategoria()] });
const CAMPOS = [
  ['nome', 'Nome', 'text', 120, 3], ['organizador', 'Organizador', 'text', 100], ['local_campeonato', 'Local', 'text', 150],
  ['data_inicio', 'Data de início', 'date'], ['data_fim', 'Data de término', 'date'],
  ['abertura_inscricoes', 'Abertura das inscrições (Brasília)', 'datetime-local'],
  ['encerramento_inscricoes', 'Encerramento das inscrições (Brasília)', 'datetime-local'],
];

export default function FormCampeonato() {
  const { id } = useParams();
  const navegar = useNavigate();
  const [form, setForm] = useState(inicial);
  const [carregando, setCarregando] = useState(Boolean(id));
  const [erroCarga, setErroCarga] = useState('');
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  const [duplicada, setDuplicada] = useState(null);
  useEffect(() => {
    let ativo = true;
    setErro(null); setDuplicada(null); setErroCarga('');
    if (!id) { setForm(inicial()); setCarregando(false); return () => { ativo = false; }; }
    setCarregando(true);
    buscarCampeonato(id).then((c) => {
      if (!ativo) return;
      const dados = Object.fromEntries(CAMPOS.map(([campo]) => [campo, c[campo]]));
      setForm({ ...dados, abertura_inscricoes: horarioBrasilia(c.abertura_inscricoes), encerramento_inscricoes: horarioBrasilia(c.encerramento_inscricoes),
        valor_inscricao: c.valor_inscricao ?? '', link_regulamento: c.link_regulamento, observacoes: c.observacoes,
        categorias: c.categorias.map((cat) => ({ id: cat.id, chave: String(cat.id), nome: cat.nome, vagas: cat.vagas ?? '' })) });
    }).catch((falha) => { if (ativo) setErroCarga(falha.status === 404 ? 'Campeonato não encontrado.' : falha.message); })
      .finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [id, tentativa]);
  function alterar(e) { const { name, value, type, checked } = e.target; setForm((anterior) => ({ ...anterior, [name]: type === 'checkbox' ? checked : value })); setErro(null); }
  function categoria(chave, campo, valor) { setForm((anterior) => ({ ...anterior, categorias: anterior.categorias.map((c) => c.chave === chave ? { ...c, [campo]: valor } : c) })); setErro(null); }
  async function enviar(dados) {
    setEnviando(true); setErro(null);
    try {
      const c = id ? await editarCampeonato(id, dados) : await criarCampeonato(dados);
      navegar(`/campeonatos/${c.id}`, { replace: true, state: { mensagem: id ? 'Campeonato atualizado.' : 'Campeonato cadastrado.' } });
    } catch (falha) {
      if (falha.codigo === 'possivel_duplicada') setDuplicada({ dados, id: falha.campos.campeonato_id });
      else { setDuplicada(null); setErro(falha); }
    } finally { setEnviando(false); }
  }
  function salvar(e) { e.preventDefault(); enviar(prepararCampeonato(form)); }
  const errosCampo = (campo) => mensagensErro(erro?.campos?.[campo]);
  const retorno = id ? `/campeonatos/${id}` : '/campeonatos';
  if (carregando) return <Carregando texto="Carregando formulário..." />;
  if (erroCarga) return <><Alert variant="danger">{erroCarga}<div><Button variant="outline-danger" onClick={() => setTentativa(tentativa + 1)}>Tentar novamente</Button></div></Alert><Link to={retorno}>Voltar</Link></>;
  return <Card><Card.Body>
    <h1 className="h3 mb-4">{id ? 'Editar campeonato' : 'Novo campeonato'}</h1>
    {erro && <Alert variant="danger" role="alert">{erro.status === 400 ? 'Corrija os campos indicados.' : erro.message}
      {erro.status === 400 && mensagensErro(erro.campos).map((m, i) => <div key={i}>{m}</div>)}
    </Alert>}
    <Form onSubmit={salvar}><fieldset disabled={enviando}>
      <Row className="g-3 mb-4">{CAMPOS.map(([campo, rotulo, tipo, max, min]) => <Col xs={12} md={campo === 'nome' ? 12 : 6} key={campo}>
        <Form.Group controlId={`campeonato-${campo}`}><Form.Label>{rotulo}</Form.Label>
          <Form.Control required name={campo} type={tipo} value={form[campo]} onChange={alterar} maxLength={max} minLength={min}
            step={tipo === 'datetime-local' ? 1 : undefined} min={campo === 'data_fim' ? form.data_inicio : undefined} isInvalid={errosCampo(campo).length > 0} />
          <Form.Control.Feedback type="invalid">{errosCampo(campo).join(' ')}</Form.Control.Feedback>
        </Form.Group>
      </Col>)}</Row>
      <Card className="mb-4"><Card.Body><h2 className="h5">Categorias</h2>
        <p className="text-muted">Cadastre ao menos uma categoria. Deixe as vagas em branco para não limitar inscrições.</p>
        {id && <p className="small text-muted">Categorias vinculadas a inscrições ou partidas não podem ser removidas.</p>}
        {form.categorias.map((c, indice) => <Row className="g-2 align-items-end mb-3" key={c.chave}>
          <Col xs={12} md={6}><Form.Group controlId={`categoria-nome-${c.chave}`}><Form.Label>Nome da categoria {indice + 1}</Form.Label><Form.Control required minLength={2} maxLength={50} value={c.nome} onChange={(e) => categoria(c.chave, 'nome', e.target.value)} /></Form.Group></Col>
          <Col xs={8} md={3}><Form.Group controlId={`categoria-vagas-${c.chave}`}><Form.Label>Vagas (opcional)</Form.Label><Form.Control type="number" min={1} max={32767} step={1} value={c.vagas} onChange={(e) => categoria(c.chave, 'vagas', e.target.value)} /></Form.Group></Col>
          <Col xs={4} md={3}><Button variant="outline-danger" disabled={form.categorias.length === 1} aria-label={`Remover categoria ${indice + 1}`} onClick={() => setForm({ ...form, categorias: form.categorias.filter((item) => item.chave !== c.chave) })}>Remover</Button></Col>
        </Row>)}
        {errosCampo('categorias').length > 0 && <Alert variant="danger">{errosCampo('categorias').join(' ')}</Alert>}
        <Button variant="outline-primary" onClick={() => setForm({ ...form, categorias: [...form.categorias, novaCategoria()] })}>Adicionar categoria</Button>
      </Card.Body></Card>
      <Row className="g-3 mb-3"><Col xs={12} md={4}><Form.Group controlId="campeonato-valor"><Form.Label>Valor da inscrição (R$, opcional)</Form.Label><Form.Control name="valor_inscricao" type="number" min={0} max={99999999.99} step="0.01" value={form.valor_inscricao} onChange={alterar} /></Form.Group></Col>
        <Col xs={12} md={8}><Form.Group controlId="campeonato-link"><Form.Label>Link do regulamento (opcional)</Form.Label><Form.Control name="link_regulamento" type="url" maxLength={255} value={form.link_regulamento} onChange={alterar} placeholder="https://" /></Form.Group></Col>
      </Row>
      <Form.Group controlId="campeonato-observacoes" className="mb-3"><Form.Label>Observações (opcional)</Form.Label><Form.Control as="textarea" rows={4} maxLength={1000} name="observacoes" value={form.observacoes} onChange={alterar} /></Form.Group>
      {!id && <Form.Check className="mb-4" id="campeonato-anunciar" name="anunciar" label="Anunciar no quadro de avisos" checked={form.anunciar} onChange={alterar} />}
      <div className="d-flex gap-2"><Button type="submit">{enviando ? 'Salvando...' : 'Salvar campeonato'}</Button><Button as={Link} to={retorno} variant="outline-secondary" disabled={enviando}>Cancelar</Button></div>
    </fieldset></Form>
    <Modal show={Boolean(duplicada)} onHide={() => { if (!enviando) setDuplicada(null); }} backdrop={enviando ? 'static' : true} keyboard={!enviando}>
      <Modal.Header closeButton={!enviando}><Modal.Title>Possível duplicidade</Modal.Title></Modal.Header><Modal.Body>Já existe um campeonato com o mesmo nome e data de início. Deseja salvar mesmo assim?
        {duplicada?.id && <p className="mt-2"><Link to={`/campeonatos/${duplicada.id}`} target="_blank" rel="noopener noreferrer">Consultar campeonato existente (nova aba)</Link></p>}
      </Modal.Body><Modal.Footer><Button variant="outline-secondary" disabled={enviando} onClick={() => setDuplicada(null)}>Voltar ao formulário</Button><Button disabled={enviando} onClick={() => enviar({ ...duplicada.dados, confirmar_duplicada: true })}>{enviando ? 'Salvando...' : 'Salvar mesmo assim'}</Button></Modal.Footer>
    </Modal>
  </Card.Body></Card>;
}
