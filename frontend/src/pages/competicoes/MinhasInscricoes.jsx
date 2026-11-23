import { useEffect, useState } from 'react';
import { Alert, Button, Modal, Table } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { minhasInscricoes, cancelarInscricao } from '../../api/competicoes';
import Carregando from '../../components/Carregando';

export default function MinhasInscricoes() {
  const [dados, setDados] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [tentativa, setTentativa] = useState(0);
  const [alvo, setAlvo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [erroAcao, setErroAcao] = useState('');
  useEffect(() => {
    let ativo = true; setCarregando(true); setErro('');
    minhasInscricoes().then(r => { if (ativo) setDados(r); }).catch(e => { if (ativo) setErro(e.message); }).finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, [tentativa]);
  async function confirmar() {
    setEnviando(true); setErroAcao('');
    try {
      await cancelarInscricao(alvo.id);
      setDados(dados.map(i => i.id === alvo.id ? { ...i, status: 'cancelada' } : i)); setAlvo(null);
    } catch(e) { setErroAcao(e.message); } finally { setEnviando(false); }
  }
  return <><h1 className="h3">Minhas inscrições</h1><Link to="/campeonatos">Ver campeonatos</Link>
    <p className="mt-3">O cancelamento é permitido durante o período de inscrições. Para trocar de categoria, cancele a anterior e inscreva-se na nova, conforme a disponibilidade de vagas.</p>
    {carregando ? <Carregando /> : erro ? <Alert variant="danger">{erro} <Button onClick={() => setTentativa(tentativa + 1)}>Tentar novamente</Button></Alert> : !dados.length ? <Alert variant="info">Você ainda não possui inscrições.</Alert> :
      <Table responsive striped><thead><tr><th>Campeonato</th><th>Categoria</th><th>Status</th><th>Ações</th></tr></thead><tbody>{dados.map(i => <tr key={i.id}>
        <td><Link to={`/campeonatos/${i.campeonato.id}`}>{i.campeonato.nome}</Link></td><td>{i.categoria.nome}</td><td>{i.status === 'ativa' ? 'Ativa' : 'Cancelada'}</td>
        <td>{i.status === 'ativa' && <Button variant="outline-danger" size="sm" onClick={() => { setAlvo(i); setErroAcao(''); }}>Cancelar inscrição</Button>}</td>
      </tr>)}</tbody></Table>}
    <Modal show={!!alvo} onHide={() => !enviando && setAlvo(null)} backdrop={enviando ? 'static' : true} keyboard={!enviando}>
      <Modal.Header closeButton={!enviando}><Modal.Title>Cancelar inscrição</Modal.Title></Modal.Header>
      <Modal.Body>{erroAcao && <Alert variant="danger" role="alert">{erroAcao}</Alert>}Confirma o cancelamento em {alvo?.campeonato.nome}, categoria {alvo?.categoria.nome}? A vaga será liberada.</Modal.Body>
      <Modal.Footer><Button variant="secondary" disabled={enviando} onClick={() => setAlvo(null)}>Voltar</Button><Button variant="danger" disabled={enviando} onClick={confirmar}>{enviando ? 'Cancelando...' : 'Confirmar cancelamento'}</Button></Modal.Footer>
    </Modal></>;
}
