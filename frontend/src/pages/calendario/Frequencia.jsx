import { useState } from "react";
import { Alert, Badge, Button, ButtonGroup, Card, Col, Form, Nav, Row, Table } from "react-bootstrap";
import { Link } from "react-router-dom";

import { buscarFrequencia, buscarFrequenciaEquipe } from "../../api/calendario";
import AlertaErro from "../../components/AlertaErro";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData, hojeISO } from "../../utils/formatacao";

const LIMITE_DESTAQUE = 50; // UC11-a.3: abaixo de 50% o atleta é destacado
const MSG_SEM_TREINOS = "Não houve treinos neste período";

const formatarPct = (p) => (p === null ? "—" : `${String(p).replace(".", ",")}%`);
const diaMes = (iso) => formatarData(iso).slice(0, 5);

// Erros 400 de período vêm por campo ({ fim: ["…"] }); os demais, como mensagem geral.
function ErroPeriodo({ erro }) {
  if (!erro) return null;
  if (erro.status === 400) return <Alert variant="danger">{Object.values(erro.campos).flat().join(" ")}</Alert>;
  return <AlertaErro erro={erro} />;
}

// UC11 · Relatório de frequência: individual (todos) e matriz da equipe com exportação em CSV (Diretor).
export default function Frequencia() {
  const { ehDiretor } = useAuth();
  const [aba, setAba] = useState("individual");
  const [personalizado, setPersonalizado] = useState(false);
  const [mes, setMes] = useState(hojeISO().slice(0, 7));
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");

  const periodo = personalizado && inicio && fim ? { inicio, fim } : { mes };
  const equipe = ehDiretor && aba === "equipe";
  const { dados, carregando, erro } = useApi(
    () => (equipe ? buscarFrequenciaEquipe(periodo) : buscarFrequencia(periodo)),
    [equipe, periodo.mes, periodo.inicio, periodo.fim],
  );

  return (
    <Card>
      <Card.Body>
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <h1 className="h4 mb-0">Frequência</h1>
          {ehDiretor && <Button as={Link} to="/frequencia/ajustar" variant="outline-primary">Ajustar presenças</Button>}
        </div>

        {ehDiretor && (
          <Nav variant="tabs" activeKey={aba} onSelect={setAba} className="mb-3">
            <Nav.Item><Nav.Link eventKey="individual">Individual</Nav.Link></Nav.Item>
            <Nav.Item><Nav.Link eventKey="equipe">Equipe</Nav.Link></Nav.Item>
          </Nav>
        )}

        {/* Filtro de mês/ano ou período personalizado (UC11-c) */}
        <Row className="g-2 align-items-end mb-3">
          <Col xs="auto">
            <ButtonGroup size="sm">
              <Button variant={personalizado ? "outline-primary" : "primary"} onClick={() => setPersonalizado(false)}>Mês</Button>
              <Button variant={personalizado ? "primary" : "outline-primary"} onClick={() => setPersonalizado(true)}>Período</Button>
            </ButtonGroup>
          </Col>
          {!personalizado ? (
            <Col xs="auto">
              <Form.Control type="month" size="sm" aria-label="Mês" value={mes}
                onChange={(e) => e.target.value && setMes(e.target.value)} />
            </Col>
          ) : (
            <>
              <Col xs="auto">
                <Form.Label className="small mb-0" htmlFor="inicio">De</Form.Label>
                <Form.Control id="inicio" type="date" size="sm" value={inicio} onChange={(e) => setInicio(e.target.value)} />
              </Col>
              <Col xs="auto">
                <Form.Label className="small mb-0" htmlFor="fim">Até</Form.Label>
                <Form.Control id="fim" type="date" size="sm" value={fim} onChange={(e) => setFim(e.target.value)} />
              </Col>
            </>
          )}
        </Row>

        {carregando && <Carregando />}
        <ErroPeriodo erro={erro} />
        {!carregando && dados && (equipe ? <MatrizEquipe dados={dados} /> : <RelatorioIndividual dados={dados} />)}
      </Card.Body>
    </Card>
  );
}

function RelatorioIndividual({ dados }) {
  if (!dados.atleta) return null; // troca de aba: espera os dados certos
  if (dados.total_treinos === 0) return <EstadoVazio mensagem={MSG_SEM_TREINOS} />;
  return (
    <>
      <Row className="g-2 mb-3 text-center">
        <Col><Card body><div className="h4 mb-0">{dados.total_treinos}</div><small className="text-muted">treinos realizados</small></Card></Col>
        <Col><Card body><div className="h4 mb-0">{dados.presencas}</div><small className="text-muted">presenças</small></Card></Col>
        <Col>
          <Card body className={dados.percentual < LIMITE_DESTAQUE ? "border-danger" : undefined}>
            <div className="h4 mb-0">{formatarPct(dados.percentual)}</div><small className="text-muted">de frequência</small>
          </Card>
        </Col>
      </Row>
      <Table responsive hover size="sm" className="align-middle">
        <thead><tr><th>Data</th><th>Treino</th><th>Situação</th><th>Registrado por</th></tr></thead>
        <tbody>
          {dados.treinos.map((t) => (
            <tr key={t.id}>
              <td>{formatarData(t.data)}</td>
              <td><Link to={`/eventos/${t.id}`}>{t.titulo}</Link></td>
              <td>{t.presente ? <Badge bg="success">Presente</Badge> : <Badge bg="secondary">Ausente</Badge>}</td>
              <td>
                {!t.registrado_por ? "—"
                  : t.registrado_por.id === dados.atleta.id ? "o próprio atleta" : t.registrado_por.nome}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </>
  );
}

function MatrizEquipe({ dados }) {
  const [ordem, setOrdem] = useState("nome");
  const [curso, setCurso] = useState("");
  if (!dados.atletas) return null;
  if (dados.treinos.length === 0) return <EstadoVazio mensagem={MSG_SEM_TREINOS} />;

  const cursos = [...new Map(dados.atletas.map((l) => [l.curso.id, l.curso.nome])).entries()]
    .sort((a, b) => a[1].localeCompare(b[1]));
  const linhas = dados.atletas
    .filter((l) => !curso || String(l.curso.id) === curso)
    .sort((a, b) => (ordem === "nome"
      ? a.atleta.nome.localeCompare(b.atleta.nome)
      : (b.percentual ?? -1) - (a.percentual ?? -1) || a.atleta.nome.localeCompare(b.atleta.nome)));

  // UC11-b: o CSV leva exatamente o que está na tela (filtro e ordem aplicados)
  function exportarCsv() {
    const cabecalho = ["Atleta", "NUSP", "Curso", ...dados.treinos.map((t) => formatarData(t.data)), "Presenças", "Frequência (%)"];
    const corpo = linhas.map((l) => [
      l.atleta.nome, l.atleta.nusp, l.curso.nome,
      ...dados.treinos.map((t) => (l.presencas.includes(t.id) ? "P" : "F")),
      l.total, l.percentual === null ? "" : String(l.percentual).replace(".", ","),
    ]);
    const csv = [cabecalho, ...corpo]
      .map((linha) => linha.map((c) => `"${String(c).replaceAll('"', '""')}"`).join(";"))
      .join("\r\n");
    const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `frequencia_${dados.inicio}_${dados.fim}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <Row className="g-2 align-items-center mb-2">
        <Col xs="auto">
          <Form.Select size="sm" aria-label="Ordenar" value={ordem} onChange={(e) => setOrdem(e.target.value)}>
            <option value="nome">Ordenar por nome</option>
            <option value="frequencia">Ordenar por frequência</option>
          </Form.Select>
        </Col>
        <Col xs="auto">
          <Form.Select size="sm" aria-label="Curso" value={curso} onChange={(e) => setCurso(e.target.value)}>
            <option value="">Todos os cursos</option>
            {cursos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
          </Form.Select>
        </Col>
        <Col className="text-end">
          <Button size="sm" variant="outline-primary" onClick={exportarCsv}>Exportar CSV</Button>
        </Col>
      </Row>
      <p className="small text-muted mb-2">
        {dados.treinos.length} treinos realizados · em vermelho, frequência abaixo de {LIMITE_DESTAQUE}%
      </p>
      <Table responsive bordered size="sm" className="align-middle text-center">
        <thead>
          <tr>
            <th className="text-start">Atleta</th>
            {dados.treinos.map((t) => <th key={t.id} title={`${formatarData(t.data)} · ${t.titulo}`}>{diaMes(t.data)}</th>)}
            <th>Total</th>
            <th>%</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={l.atleta.id} className={l.percentual < LIMITE_DESTAQUE ? "table-danger" : undefined}>
              <td className="text-start text-nowrap">{l.atleta.nome}<div className="small text-muted">{l.curso.nome}</div></td>
              {dados.treinos.map((t) => (
                <td key={t.id}>{l.presencas.includes(t.id) ? "✓" : <span className="text-muted">–</span>}</td>
              ))}
              <td>{l.total}</td>
              <td className="fw-semibold">{formatarPct(l.percentual)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </>
  );
}
