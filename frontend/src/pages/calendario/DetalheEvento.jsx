import { useState } from "react";
import { Alert, Badge, Button, Card, CloseButton, Form, Modal, Stack, Table } from "react-bootstrap";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  buscarEvento,
  cancelarEvento,
  listarPresencas,
  registrarPresencas,
  removerPresenca,
} from "../../api/calendario";
import AlertaErro from "../../components/AlertaErro";
import ErroCampo from "../../components/ErroCampo";
import BadgeStatus from "../../components/BadgeStatus";
import BuscaAtleta from "../../components/BuscaAtleta";
import Carregando from "../../components/Carregando";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData, formatarDataHora } from "../../utils/formatacao";
import { CORES_TIPO_CALENDARIO, rotulo } from "../../utils/rotulos";

// Mesmo texto que a API devolve fora da janela (UC09-c)
const msgForaDaJanela = (j) =>
  `O registro de presença para este treino está disponível das ${j.inicio} às ${j.fim}. ` +
  "Para ajustes fora desse horário, procure a Diretoria";

// Detalhe do evento (UC08 passo 4) e, se for treino, a presença (UC09): confirmar a minha,
// adicionar colegas, ver quem registrou e remover um registro feito por engano.
export default function DetalheEvento() {
  const { id } = useParams();
  const location = useLocation();
  const { usuario, ehDiretor } = useAuth();
  const { dados, carregando, erro, recarregar } = useApi(async () => {
    const evento = await buscarEvento(id);
    return evento.tipo === "treino" ? listarPresencas(id) : { evento };
  }, [id]);
  const [mensagem, setMensagem] = useState(location.state?.mensagem || null); // ex.: "Evento criado"
  const [erroAcao, setErroAcao] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [adicionando, setAdicionando] = useState(false);
  const [colegas, setColegas] = useState([]);
  const [removendo, setRemovendo] = useState(null);
  const [cancelando, setCancelando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [erroCancelar, setErroCancelar] = useState(null);

  if (carregando && !dados) return <Carregando />;
  if (erro) return <AlertaErro erro={erro.status === 404 ? "Evento não encontrado." : erro} />;
  if (!dados) return null;

  const { evento, janela, dentro_da_janela: dentro, presencas = [] } = dados;
  const ehTreino = evento.tipo === "treino";
  const cancelado = evento.status === "cancelado";
  const podeRegistrar = ehTreino && !cancelado && dentro;

  async function executar(acao) {
    setErroAcao(null);
    setMensagem(null);
    setEnviando(true);
    try {
      await acao();
      await recarregar();
    } catch (falha) {
      setErroAcao(falha);
    } finally {
      setEnviando(false);
    }
  }

  // UC09 passo 6 e UC09-e: "Presença registrada" e aviso de quem já estava presente
  function resumo({ registrados, ja_presentes: jaPresentes }, nomes) {
    const partes = [];
    if (registrados.length) partes.push("Presença registrada");
    if (jaPresentes.length) {
      const quem = jaPresentes.map((i) => (i === usuario.id ? "você" : nomes[i])).join(", ");
      partes.push(`Já estava${jaPresentes.length > 1 ? "m" : ""} presente${jaPresentes.length > 1 ? "s" : ""}: ${quem}`);
    }
    return partes.join(". ");
  }

  const confirmarMinha = () => executar(async () => {
    setMensagem(resumo(await registrarPresencas(evento.id), {}));
  });

  const confirmarColegas = () => executar(async () => {
    const nomes = Object.fromEntries(colegas.map((c) => [c.id, c.nome]));
    setMensagem(resumo(await registrarPresencas(evento.id, colegas.map((c) => c.id)), nomes));
    setColegas([]);
    setAdicionando(false);
  });

  const confirmarRemocao = () => executar(async () => {
    await removerPresenca(evento.id, removendo.atleta.id);
    setRemovendo(null);
  });

  // UC07-b: status Cancelado com motivo opcional; o evento continua visível no calendário
  async function confirmarCancelamento() {
    setErroCancelar(null);
    setEnviando(true);
    try {
      await cancelarEvento(evento.id, motivo.trim());
      setCancelando(false);
      setMotivo("");
      await recarregar();
    } catch (falha) {
      setErroCancelar(falha);
    } finally {
      setEnviando(false);
    }
  }

  function escolherColega(atleta) {
    if (atleta && !colegas.some((c) => c.id === atleta.id)) setColegas([...colegas, atleta]);
  }

  // UC09-b: o autor remove dentro da janela; o Diretor sempre (UC10)
  const podeRemover = (p) => ehDiretor || (p.registrado_por.id === usuario.id && podeRegistrar);

  return (
    <>
      {mensagem && <Alert variant="success" dismissible onClose={() => setMensagem(null)}>{mensagem}</Alert>}
      <AlertaErro erro={erroAcao} onFechar={() => setErroAcao(null)} />

      <Card className="mb-3">
        <Card.Body>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <Badge bg={CORES_TIPO_CALENDARIO[evento.tipo]}>{rotulo("tipoEvento", evento.tipo)}</Badge>
            <BadgeStatus status={evento.status} grupo="statusEvento" />
          </div>
          <h1 className="h4">{evento.titulo}</h1>
          <p className="mb-1">
            {formatarData(evento.data_evento)} · {evento.hora_inicio}–{evento.hora_fim} · {evento.local_evento}
          </p>
          {evento.descricao && <p className="text-muted mb-1" style={{ whiteSpace: "pre-line" }}>{evento.descricao}</p>}
          {cancelado && evento.motivo_cancelamento && (
            <p className="text-danger mb-1">Motivo do cancelamento: {evento.motivo_cancelamento}</p>
          )}
          <div className="d-flex flex-wrap gap-2 mt-3">
            <Button as={Link} to="/calendario" variant="outline-primary">Voltar ao calendário</Button>
            {ehDiretor && !cancelado && (
              <>
                <Button as={Link} to={`/eventos/${evento.id}/editar`}>Editar</Button>
                <Button variant="outline-danger" onClick={() => setCancelando(true)}>Cancelar evento</Button>
              </>
            )}
          </div>
        </Card.Body>
      </Card>

      {ehTreino && (
        <Card>
          <Card.Body>
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
              <h2 className="h5 mb-0">Presença · {presencas.length} presente{presencas.length === 1 ? "" : "s"}</h2>
              {evento.presente && <Badge bg="success">Você está presente</Badge>}
            </div>

            {cancelado && <Alert variant="secondary">Este treino foi cancelado</Alert>}
            {!cancelado && !dentro && <Alert variant="info">{msgForaDaJanela(janela)}</Alert>}

            {podeRegistrar && (
              <Stack direction="horizontal" gap={2} className="flex-wrap mb-3">
                <Button onClick={confirmarMinha} disabled={enviando || evento.presente}>
                  Confirmar minha presença
                </Button>
                <Button variant="outline-primary" onClick={() => setAdicionando(!adicionando)} disabled={enviando}>
                  Adicionar colega
                </Button>
              </Stack>
            )}

            {podeRegistrar && adicionando && (
              <Card body className="mb-3 bg-body-tertiary">
                {/* key muda a cada escolha: o campo de busca volta vazio para o próximo colega */}
                <BuscaAtleta key={colegas.length} valor={null} onSelect={escolherColega} />
                {colegas.length > 0 && (
                  <div className="d-flex flex-wrap gap-2 mt-2">
                    {colegas.map((c) => (
                      <Badge key={c.id} bg="light" text="dark" className="d-flex align-items-center gap-1 border">
                        {c.nome}
                        <CloseButton aria-label={`Tirar ${c.nome}`} style={{ fontSize: "0.5rem" }}
                          onClick={() => setColegas(colegas.filter((x) => x.id !== c.id))} />
                      </Badge>
                    ))}
                  </div>
                )}
                <Button size="sm" className="mt-2" onClick={confirmarColegas} disabled={enviando || colegas.length === 0}>
                  Registrar presença {colegas.length > 1 ? `dos ${colegas.length} colegas` : "do colega"}
                </Button>
              </Card>
            )}

            {presencas.length === 0 ? (
              <p className="text-muted mb-0">Nenhuma presença registrada ainda.</p>
            ) : (
              <Table responsive size="sm" className="align-middle mb-0">
                <thead>
                  <tr><th>Atleta</th><th>Registrado em</th><th>Registrado por</th><th /></tr>
                </thead>
                <tbody>
                  {presencas.map((p) => (
                    <tr key={p.atleta.id}>
                      <td>{p.atleta.nome}</td>
                      <td>{formatarDataHora(p.data_registro)}</td>
                      <td>{p.registrado_por.id === p.atleta.id ? "o próprio atleta" : p.registrado_por.nome}</td>
                      <td className="text-end">
                        {podeRemover(p) && (
                          <Button size="sm" variant="outline-danger" onClick={() => setRemovendo(p)} disabled={enviando}>
                            Remover
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card.Body>
        </Card>
      )}

      <Modal show={cancelando} onHide={() => setCancelando(false)} centered>
        <Modal.Header closeButton><Modal.Title className="h5">Cancelar evento</Modal.Title></Modal.Header>
        <Modal.Body>
          <p>
            "{evento.titulo}" continuará no calendário marcado como cancelado, e os atletas ativos serão avisados.
          </p>
          <AlertaErro erro={erroCancelar && !erroCancelar.campos?.motivo ? erroCancelar : null} />
          <Form.Group controlId="motivo">
            <Form.Label>Motivo (opcional)</Form.Label>
            <Form.Control as="textarea" rows={3} maxLength={200} value={motivo}
              onChange={(e) => setMotivo(e.target.value)} isInvalid={Boolean(erroCancelar?.campos?.motivo)} />
            <Form.Text muted>{motivo.length}/200</Form.Text>
            <ErroCampo erro={erroCancelar} campo="motivo" />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setCancelando(false)}>Voltar</Button>
          <Button variant="danger" onClick={confirmarCancelamento} disabled={enviando}>Cancelar evento</Button>
        </Modal.Footer>
      </Modal>

      <Modal show={Boolean(removendo)} onHide={() => setRemovendo(null)} centered>
        <Modal.Header closeButton><Modal.Title className="h5">Remover presença</Modal.Title></Modal.Header>
        <Modal.Body>Remover a presença de {removendo?.atleta.nome} neste treino?</Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setRemovendo(null)}>Cancelar</Button>
          <Button variant="danger" onClick={confirmarRemocao} disabled={enviando}>Remover</Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
