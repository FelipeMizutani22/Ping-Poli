import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Col, Form, ListGroup, Modal, Row } from "react-bootstrap";
import { useSearchParams } from "react-router-dom";

import { buscarAjuste, listarCalendario, salvarAjuste } from "../../api/calendario";
import AlertaErro from "../../components/AlertaErro";
import BadgeStatus from "../../components/BadgeStatus";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import ErroCampo from "../../components/ErroCampo";
import { useApi } from "../../hooks/useApi";
import { formatarData, formatarDataHora, hojeISO } from "../../utils/formatacao";

// "AAAA-MM" → primeiro e último dia do mês
function limitesDoMes(mes) {
  const [ano, m] = mes.split("-").map(Number);
  const ultimo = new Date(ano, m, 0).getDate();
  return { inicio: `${mes}-01`, fim: `${mes}-${String(ultimo).padStart(2, "0")}` };
}

// UC10 · Ajustar presenças (Diretor): treinos do mês → atletas ativos com caixa de presença.
// Sem a janela de horário; remoções pedem justificativa; cada mudança vai para a auditoria.
export default function AjustarPresencas() {
  const [params, setParams] = useSearchParams();
  const mes = params.get("mes") || hojeISO().slice(0, 7);
  const eventoId = params.get("evento");
  const { dados: treinos, carregando, erro, recarregar } = useApi(
    () => listarCalendario({ ...limitesDoMes(mes), tipo: "treino" }), [mes],
  );

  function escolher(mudancas) {
    const novo = new URLSearchParams(params);
    Object.entries(mudancas).forEach(([k, v]) => (v ? novo.set(k, v) : novo.delete(k)));
    setParams(novo);
  }

  return (
    <Row className="g-3">
      <Col lg={5}>
        <Card>
          <Card.Body>
            <h1 className="h4 mb-3">Ajustar presenças</h1>
            <Form.Group className="mb-3" controlId="mes">
              <Form.Label>Mês</Form.Label>
              <Form.Control type="month" value={mes} onChange={(e) => e.target.value && escolher({ mes: e.target.value, evento: null })} />
            </Form.Group>

            {carregando && <Carregando />}
            <AlertaErro erro={erro} />
            {treinos && treinos.length === 0 && <EstadoVazio mensagem="Nenhum treino neste período" />}
            {treinos && treinos.length > 0 && (
              <ListGroup>
                {treinos.map((t) => (
                  <ListGroup.Item key={t.id} action active={String(t.id) === eventoId}
                    onClick={() => escolher({ evento: String(t.id) })}
                    className="d-flex justify-content-between align-items-center gap-2">
                    <span>
                      {formatarData(t.data)} · {t.titulo}
                      {t.status === "cancelado" && <> <BadgeStatus status="cancelado" grupo="statusEvento" /></>}
                    </span>
                    <Badge bg="light" text="dark">{t.total_presentes} presente{t.total_presentes === 1 ? "" : "s"}</Badge>
                  </ListGroup.Item>
                ))}
              </ListGroup>
            )}
          </Card.Body>
        </Card>
      </Col>
      <Col lg={7}>
        {eventoId
          ? <PainelAjuste key={eventoId} eventoId={eventoId} aoSalvar={recarregar} aoFechar={() => escolher({ evento: null })} />
          : <Card body className="text-muted">Selecione um treino para ajustar as presenças.</Card>}
      </Col>
    </Row>
  );
}

function PainelAjuste({ eventoId, aoSalvar, aoFechar }) {
  const { dados, carregando, erro, recarregar } = useApi(() => buscarAjuste(eventoId), [eventoId]);
  const [marcados, setMarcados] = useState(new Set());
  const [pedindoJustificativa, setPedindoJustificativa] = useState(false);
  const [justificativa, setJustificativa] = useState("");
  const [erroSalvar, setErroSalvar] = useState(null);
  const [mensagem, setMensagem] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const originais = new Set((dados?.atletas || []).filter((l) => l.presente).map((l) => l.atleta.id));

  // Volta às caixas como estão gravadas sempre que os dados chegam (também é o "Cancelar", UC10-a)
  useEffect(() => {
    if (dados) setMarcados(new Set(dados.atletas.filter((l) => l.presente).map((l) => l.atleta.id)));
  }, [dados]);

  if (carregando && !dados) return <Carregando />;
  if (erro) return <AlertaErro erro={erro} />;
  if (!dados) return null;

  const { evento, ajustavel } = dados;
  const removidos = [...originais].filter((id) => !marcados.has(id));
  const incluidos = [...marcados].filter((id) => !originais.has(id));
  const mudou = removidos.length + incluidos.length > 0;

  function alternar(id) {
    const novo = new Set(marcados);
    if (novo.has(id)) novo.delete(id);
    else novo.add(id);
    setMarcados(novo);
  }

  async function gravar() {
    setErroSalvar(null);
    setEnviando(true);
    try {
      await salvarAjuste(evento.id, [...marcados], justificativa.trim());
      setPedindoJustificativa(false);
      setJustificativa("");
      setMensagem("Presenças atualizadas");
      await recarregar();
      aoSalvar();
    } catch (falha) {
      setErroSalvar(falha);
    } finally {
      setEnviando(false);
    }
  }

  // UC10 passo 6: só pede justificativa se houver remoções
  function salvar() {
    setMensagem(null);
    if (removidos.length) setPedindoJustificativa(true);
    else gravar();
  }

  return (
    <Card>
      <Card.Body>
        <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
          <div>
            <h2 className="h5 mb-1">{evento.titulo}</h2>
            <div className="text-muted small">
              {formatarData(evento.data_evento)} · {evento.hora_inicio}–{evento.hora_fim} · {evento.local_evento}
            </div>
          </div>
          <Button size="sm" variant="outline-secondary" onClick={aoFechar}>Fechar</Button>
        </div>

        {mensagem && <Alert variant="success" dismissible onClose={() => setMensagem(null)}>{mensagem}</Alert>}
        {!ajustavel && <Alert variant="info">{dados.mensagem}</Alert>}
        {!pedindoJustificativa && <AlertaErro erro={erroSalvar} onFechar={() => setErroSalvar(null)} />}

        <ListGroup variant="flush" className="mb-3">
          {dados.atletas.map((l) => (
            <ListGroup.Item key={l.atleta.id} className="px-0">
              <Form.Check type="checkbox" id={`presenca-${l.atleta.id}`} disabled={!ajustavel || enviando}
                checked={marcados.has(l.atleta.id)} onChange={() => alternar(l.atleta.id)}
                label={
                  <>
                    {l.atleta.nome}
                    {l.presente && (
                      <small className="text-muted ms-2">
                        registrado por {l.registrado_por.id === l.atleta.id ? "o próprio atleta" : l.registrado_por.nome}
                        {" "}em {formatarDataHora(l.data_registro)}
                      </small>
                    )}
                  </>
                } />
            </ListGroup.Item>
          ))}
        </ListGroup>

        {ajustavel && (
          <div className="d-flex flex-wrap align-items-center gap-2">
            <Button onClick={salvar} disabled={!mudou || enviando}>Salvar</Button>
            <Button variant="outline-secondary" disabled={!mudou || enviando}
              onClick={() => setMarcados(new Set(originais))}>Cancelar</Button>
            {mudou && (
              <small className="text-muted">
                {incluidos.length} inclusão(ões) · {removidos.length} remoção(ões)
              </small>
            )}
          </div>
        )}
      </Card.Body>

      <Modal show={pedindoJustificativa} onHide={() => setPedindoJustificativa(false)} centered>
        <Modal.Header closeButton><Modal.Title className="h5">Justificativa</Modal.Title></Modal.Header>
        <Modal.Body>
          <p>
            Você está removendo {removidos.length} presença{removidos.length > 1 ? "s" : ""}. Informe o motivo; ele fica
            registrado na auditoria.
          </p>
          <AlertaErro erro={erroSalvar && !erroSalvar.campos?.justificativa ? erroSalvar : null} />
          <Form.Control as="textarea" rows={3} maxLength={200} value={justificativa} aria-label="Justificativa"
            onChange={(e) => setJustificativa(e.target.value)} isInvalid={Boolean(erroSalvar?.campos?.justificativa)} />
          <Form.Text muted>{justificativa.length}/200 · mínimo 5 caracteres</Form.Text>
          <ErroCampo erro={erroSalvar} campo="justificativa" />
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setPedindoJustificativa(false)}>Voltar</Button>
          <Button onClick={gravar} disabled={enviando || justificativa.trim().length < 5}>Salvar</Button>
        </Modal.Footer>
      </Modal>
    </Card>
  );
}
