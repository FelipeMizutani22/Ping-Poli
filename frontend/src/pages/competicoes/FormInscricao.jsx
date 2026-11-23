import { useState } from 'react';
import { Alert, Button, Card, Form } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { inscrever } from '../../api/competicoes';
import { useAuth } from '../../contexts/AuthContext';
import { mensagensErro } from '../../utils/competicoes';

export default function FormInscricao({ campeonato: c, atualizar }) {
  const { usuario } = useAuth();
  const [selecionadas, setSelecionadas] = useState([]);
  const [observacoes, setObservacoes] = useState('');
  const [ciencia, setCiencia] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState('');
  const [sucesso, setSucesso] = useState(false);
  async function enviar(e) {
    e.preventDefault(); setErro(''); setEnviando(true); setSucesso(false);
    try {
      await inscrever({ categorias: selecionadas, observacoes, ciencia_regulamento: ciencia });
      setSelecionadas([]); setCiencia(false); setObservacoes(''); setSucesso(true);
      try { await atualizar(); } catch { setErro('A inscrição foi confirmada, mas não foi possível atualizar as vagas. Recarregue a página.'); }
    } catch (falha) {
      const ids = falha.campos?.categorias_esgotadas || [];
      const nomes = c.categorias.filter(cat => ids.includes(cat.id)).map(cat => cat.nome).join(', ');
      setErro(falha.status === 400 ? mensagensErro(falha.campos).join(' ') : `${falha.message}${nomes ? ' Categorias: ' + nomes : ''}`);
    } finally { setEnviando(false); }
  }
  const aberta = c.status === 'inscricoes_abertas' && Date.now() < Date.parse(c.encerramento_inscricoes);
  return <Card className="mt-4"><Card.Body><h2 className="h5">Inscrição</h2>
    <Link to="/inscricoes">Minhas inscrições e cancelamentos</Link>
    {sucesso && <Alert variant="success" className="mt-3">Inscrição confirmada.</Alert>}
    {erro && <Alert variant="danger" role="alert" className="mt-3">{erro}</Alert>}
    {!aberta ? <p className="mt-3">As inscrições não estão abertas.</p> : <Form onSubmit={enviar} className="mt-3">
      <p>{usuario.nome} · NUSP {usuario.nusp} · {usuario.curso?.nome}</p>
      <fieldset disabled={enviando}><legend className="h6">Selecione as novas categorias</legend>
        {c.categorias.map(cat => <Form.Check key={cat.id} id={`inscricao-${cat.id}`} type="checkbox"
          label={`${cat.nome} — ${cat.inscrito ? 'Já inscrito' : cat.vagas_restantes === null ? 'Sem limite de vagas' : cat.vagas_restantes + ' vaga(s)'}`}
          disabled={cat.inscrito || cat.vagas_restantes === 0} checked={cat.inscrito || selecionadas.includes(cat.id)}
          onChange={e => setSelecionadas(e.target.checked ? [...selecionadas, cat.id] : selecionadas.filter(id => id !== cat.id))} />)}
        <Form.Group controlId="inscricao-observacoes" className="my-3"><Form.Label>Observações (opcional)</Form.Label><Form.Control as="textarea" maxLength={300} value={observacoes} onChange={e => setObservacoes(e.target.value)} /><Form.Text>Até 300 caracteres.</Form.Text></Form.Group>
        <Form.Check id="inscricao-ciencia" required label="Declaro ciência do regulamento" checked={ciencia} onChange={e => setCiencia(e.target.checked)} />
        <Button type="submit" className="mt-3" disabled={!selecionadas.length || !ciencia}>{enviando ? 'Confirmando...' : 'Confirmar inscrição'}</Button>
      </fieldset>
    </Form>}
  </Card.Body></Card>;
}
