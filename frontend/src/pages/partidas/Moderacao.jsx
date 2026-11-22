import { useState } from "react";
import { Alert, Button, ButtonGroup, Card, Col, Form, Row, Tab, Table, Tabs } from "react-bootstrap";

import { listarPartidas } from "../../api/partidas";
import AlertaErro from "../../components/AlertaErro";
import BadgeStatus from "../../components/BadgeStatus";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import PlacarSets from "../../components/PlacarSets";
import { useApi } from "../../hooks/useApi";
import { formatarData } from "../../utils/formatacao";
import { ROTULOS } from "../../utils/rotulos";
import ModalHistorico from "./ModalHistorico";
import ModalModerar from "./ModalModerar";

function nomeAdversario(p) {
  return p.adversario?.nome || p.adversario_externo?.nome;
}

// UC17 · Moderação de partidas (só Diretor): abas "Contestadas" e "Todas"
export default function Moderacao() {
  const [aba, setAba] = useState("contestadas");
  const [filtros, setFiltros] = useState({ status: "", tipo_adversario: "", inicio: "", fim: "" });
  const [acao, setAcao] = useState(null); // { partida, decisao } ou { partida, historico: true }
  const [mensagem, setMensagem] = useState(null);

  const contestadas = useApi(() => listarPartidas({ escopo: "contestadas" }), []);
  const todas = useApi(() => listarPartidas({ escopo: "todas", ...filtros }), [filtros]);

  function aoModerar(texto) {
    setAcao(null);
    setMensagem(texto);
    contestadas.recarregar();
    todas.recarregar();
  }

  return (
    <>
      <h1 className="h4 mb-3">Moderação de partidas</h1>
      {mensagem && <Alert variant="success" dismissible onClose={() => setMensagem(null)}>{mensagem}</Alert>}

      <Tabs activeKey={aba} onSelect={setAba} className="mb-3">
        <Tab eventKey="contestadas" title={`Contestadas${contestadas.dados ? ` (${contestadas.dados.length})` : ""}`}>
          {contestadas.carregando && <Carregando />}
          <AlertaErro erro={contestadas.erro} />
          {contestadas.dados?.length === 0 && <EstadoVazio mensagem="Nenhuma contestação pendente" />}
          {contestadas.dados?.map((p) => (
            <Card key={p.id} className="mb-3 border-danger-subtle">
              <Card.Body>
                <div className="d-flex justify-content-between flex-wrap gap-2">
                  <div>
                    <strong>{p.atleta.nome} × {nomeAdversario(p)}</strong>
                    <span className="text-muted"> · {formatarData(p.data_jogo)} · {p.competicao.nome}</span>
                  </div>
                  <Button size="sm" variant="link" onClick={() => setAcao({ partida: p, historico: true })}>Histórico</Button>
                </div>
                <Row className="mt-2 g-2">
                  <Col md={6}>
                    <div className="small text-muted">Placar registrado ({p.atleta.nome})</div>
                    <div><PlacarSets sets={p.sets} /> <span className="text-muted">({p.placar_sets.atleta}–{p.placar_sets.adversario})</span></div>
                  </Col>
                  <Col md={6}>
                    <div className="small text-muted">Placar proposto ({p.contestacao?.contestante.nome})</div>
                    <div>{p.contestacao?.sets_propostos.length ? <PlacarSets sets={p.contestacao.sets_propostos} /> : <span className="text-muted">não informado</span>}</div>
                  </Col>
                </Row>
                <p className="mt-2 mb-3 small"><span className="text-muted">Justificativa:</span> {p.contestacao?.justificativa}</p>
                <ButtonGroup size="sm" className="flex-wrap">
                  <Button variant="outline-primary" onClick={() => setAcao({ partida: p, decisao: "manter" })}>Manter placar registrado</Button>
                  {p.contestacao?.sets_propostos.length > 0 && (
                    <Button variant="outline-primary" onClick={() => setAcao({ partida: p, decisao: "aceitar_proposto" })}>Aceitar placar proposto</Button>
                  )}
                  <Button variant="outline-secondary" onClick={() => setAcao({ partida: p, decisao: "editar" })}>Editar</Button>
                  <Button variant="outline-danger" onClick={() => setAcao({ partida: p, decisao: "remover" })}>Remover</Button>
                </ButtonGroup>
              </Card.Body>
            </Card>
          ))}
        </Tab>

        <Tab eventKey="todas" title="Todas">
          <Row className="g-2 mb-3">
            <Col sm={3}>
              <Form.Select size="sm" value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}>
                <option value="">Todos os status</option>
                {Object.entries(ROTULOS.statusPartida).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
              </Form.Select>
            </Col>
            <Col sm={3}>
              <Form.Select size="sm" value={filtros.tipo_adversario} onChange={(e) => setFiltros({ ...filtros, tipo_adversario: e.target.value })}>
                <option value="">Todos os adversários</option>
                {Object.entries(ROTULOS.tipoAdversario).map(([v, r]) => <option key={v} value={v}>{r}</option>)}
              </Form.Select>
            </Col>
            <Col sm={3}>
              <Form.Control size="sm" type="date" title="De" value={filtros.inicio} onChange={(e) => setFiltros({ ...filtros, inicio: e.target.value })} />
            </Col>
            <Col sm={3}>
              <Form.Control size="sm" type="date" title="Até" value={filtros.fim} onChange={(e) => setFiltros({ ...filtros, fim: e.target.value })} />
            </Col>
          </Row>
          {todas.carregando && <Carregando />}
          <AlertaErro erro={todas.erro} />
          {todas.dados?.length === 0 && <EstadoVazio mensagem="Nenhuma partida encontrada com esses filtros." />}
          {todas.dados?.length > 0 && (
            <Table hover responsive size="sm" className="align-middle">
              <thead>
                <tr><th>Data</th><th>Jogadores</th><th>Competição</th><th>Placar</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {todas.dados.map((p) => (
                  <tr key={p.id}>
                    <td>{formatarData(p.data_jogo)}</td>
                    <td>{p.atleta.nome} × {nomeAdversario(p)}</td>
                    <td>{p.competicao.nome}</td>
                    <td className="small"><PlacarSets sets={p.sets} /></td>
                    <td><BadgeStatus status={p.status} /></td>
                    <td className="text-nowrap">
                      <Button size="sm" variant="link" onClick={() => setAcao({ partida: p, historico: true })}>Histórico</Button>
                      {["confirmada", "contestada"].includes(p.status) && (
                        <Button size="sm" variant="link" onClick={() => setAcao({ partida: p, decisao: "editar" })}>Editar</Button>
                      )}
                      {p.status !== "removida" && (
                        <Button size="sm" variant="link" className="text-danger" onClick={() => setAcao({ partida: p, decisao: "remover" })}>Remover</Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Tab>
      </Tabs>

      {acao?.decisao && (
        <ModalModerar partida={acao.partida} decisao={acao.decisao} onFechar={() => setAcao(null)} onModerada={aoModerar} />
      )}
      {acao?.historico && <ModalHistorico partida={acao.partida} onFechar={() => setAcao(null)} />}
    </>
  );
}
