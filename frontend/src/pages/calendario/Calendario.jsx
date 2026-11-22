import { useState } from "react";
import { Badge, Button, ButtonGroup, Card, Form, ListGroup, Nav, Table } from "react-bootstrap";
import { Link } from "react-router-dom";

import { listarCalendario } from "../../api/calendario";
import AlertaErro from "../../components/AlertaErro";
import BadgeStatus from "../../components/BadgeStatus";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData } from "../../utils/formatacao";
import { CORES_TIPO_CALENDARIO, ROTULOS, rotulo } from "../../utils/rotulos";

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const DIAS_PROXIMOS = 30;
const MSG_VAZIO = "Nenhum evento neste período";

// "AAAA-MM-DD" de uma data local (sem passar por UTC)
function iso(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function linkDoItem(item) {
  return item.tipo === "campeonato" ? `/campeonatos/${item.id}` : `/eventos/${item.id}`;
}

// Grade do mês: semanas de domingo a sábado, com null nos dias fora do mês.
function semanasDoMes(mes) {
  const primeiro = new Date(mes.getFullYear(), mes.getMonth(), 1);
  const totalDias = new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate();
  const celulas = Array(primeiro.getDay()).fill(null);
  for (let dia = 1; dia <= totalDias; dia++) celulas.push(new Date(mes.getFullYear(), mes.getMonth(), dia));
  while (celulas.length % 7) celulas.push(null);
  const semanas = [];
  for (let i = 0; i < celulas.length; i += 7) semanas.push(celulas.slice(i, i + 7));
  return semanas;
}

// O campeonato ocupa todos os dias de `data` a `data_fim` (UC08, requerimentos especiais).
function itensDoDia(itens, diaISO) {
  return itens.filter((i) => (i.data_fim ? i.data <= diaISO && diaISO <= i.data_fim : i.data === diaISO));
}

function ItemGrade({ item }) {
  const cancelado = item.status === "cancelado";
  const texto = item.hora_inicio ? `${item.hora_inicio} ${item.titulo}` : item.titulo;
  return (
    <Link to={linkDoItem(item)} title={cancelado ? `${item.titulo} (cancelado)` : item.titulo}
      className={`item-calendario badge text-bg-${CORES_TIPO_CALENDARIO[item.tipo]} text-decoration-none`
        + (cancelado ? " item-cancelado" : "")}>
      {texto}
    </Link>
  );
}

// Calendário da equipe (UC08): visão mensal e "Próximos eventos", cores por tipo, legenda que filtra.
export default function Calendario() {
  const { ehDiretor } = useAuth();
  const hoje = new Date();
  const hojeISO = iso(hoje);
  const [mes, setMes] = useState(new Date(hoje.getFullYear(), hoje.getMonth(), 1));
  const [visao, setVisao] = useState("mes");
  const [tipos, setTipos] = useState(Object.keys(ROTULOS.tipoCalendario));

  const inicio = iso(mes);
  const fim = iso(new Date(mes.getFullYear(), mes.getMonth() + 1, 0));
  const limiteProximos = iso(new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + DIAS_PROXIMOS));
  const periodo = visao === "mes" ? { inicio, fim } : { inicio: hojeISO, fim: limiteProximos };
  const { dados, carregando, erro } = useApi(() => listarCalendario(periodo), [periodo.inicio, periodo.fim]);

  const itens = (dados || []).filter((i) => tipos.includes(i.tipo));
  const nomeMes = mes.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });

  function alternarTipo(tipo) {
    setTipos(tipos.includes(tipo) ? tipos.filter((t) => t !== tipo) : [...tipos, tipo]);
  }

  function mudarMes(delta) {
    setMes(new Date(mes.getFullYear(), mes.getMonth() + delta, 1));
  }

  return (
    <Card>
      <Card.Body>
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
          <h1 className="h4 mb-0">Calendário</h1>
          {ehDiretor && <Button as={Link} to="/eventos/novo">Novo evento</Button>}
        </div>

        <Nav variant="tabs" activeKey={visao} onSelect={setVisao} className="mb-3">
          <Nav.Item><Nav.Link eventKey="mes">Mês</Nav.Link></Nav.Item>
          <Nav.Item><Nav.Link eventKey="lista">Próximos eventos</Nav.Link></Nav.Item>
        </Nav>

        {/* Legenda de cores, que também filtra por tipo (UC08-b) */}
        <div className="d-flex flex-wrap gap-3 mb-3">
          {Object.entries(ROTULOS.tipoCalendario).map(([tipo, nome]) => (
            <Form.Check key={tipo} type="checkbox" id={`tipo-${tipo}`} checked={tipos.includes(tipo)}
              onChange={() => alternarTipo(tipo)}
              label={<Badge bg={CORES_TIPO_CALENDARIO[tipo]} text={tipo === "campeonato" ? "dark" : undefined}>{nome}</Badge>} />
          ))}
          <span className="small text-muted"><span className="item-cancelado">Riscado</span> = cancelado</span>
        </div>

        <AlertaErro erro={erro} />

        {visao === "mes" && (
          <>
            <div className="d-flex justify-content-between align-items-center mb-2">
              <ButtonGroup size="sm">
                <Button variant="outline-primary" onClick={() => mudarMes(-1)} aria-label="Mês anterior">‹</Button>
                <Button variant="outline-primary" onClick={() => setMes(new Date(hoje.getFullYear(), hoje.getMonth(), 1))}>
                  Hoje
                </Button>
                <Button variant="outline-primary" onClick={() => mudarMes(1)} aria-label="Próximo mês">›</Button>
              </ButtonGroup>
              <h2 className="h5 mb-0 text-capitalize">{nomeMes}</h2>
            </div>
            {carregando ? <Carregando /> : (
              <>
                {!erro && itens.length === 0 && <p className="text-muted text-center my-2">{MSG_VAZIO}</p>}
                <Table bordered responsive className="calendario-grade mb-0">
                  <thead><tr>{DIAS_SEMANA.map((d) => <th key={d}>{d}</th>)}</tr></thead>
                  <tbody>
                    {semanasDoMes(mes).map((semana, i) => (
                      <tr key={i}>
                        {semana.map((dia, j) => {
                          if (!dia) return <td key={j} className="bg-body-tertiary" />;
                          const diaISO = iso(dia);
                          return (
                            <td key={j} className={diaISO === hojeISO ? "dia-hoje" : undefined}>
                              <div className="dia-numero">{dia.getDate()}</div>
                              {itensDoDia(itens, diaISO).map((item) => (
                                <ItemGrade key={`${item.tipo}-${item.id}`} item={item} />
                              ))}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </>
            )}
          </>
        )}

        {visao === "lista" && (
          <>
            {carregando && <Carregando />}
            {!carregando && !erro && itens.length === 0 && <EstadoVazio mensagem={MSG_VAZIO} />}
            {!carregando && itens.length > 0 && (
              <ListGroup>
                {itens.map((item) => (
                  <ListGroup.Item key={`${item.tipo}-${item.id}`} action as={Link} to={linkDoItem(item)}
                    className="d-flex flex-wrap align-items-center gap-2">
                    <Badge bg={CORES_TIPO_CALENDARIO[item.tipo]} text={item.tipo === "campeonato" ? "dark" : undefined}>
                      {rotulo("tipoCalendario", item.tipo)}
                    </Badge>
                    <span className={item.status === "cancelado" ? "item-cancelado fw-semibold" : "fw-semibold"}>
                      {item.titulo}
                    </span>
                    {item.status === "cancelado" && <BadgeStatus status="cancelado" grupo="statusEvento" />}
                    {item.presente && <Badge bg="success">Presente</Badge>}
                    <small className="text-muted ms-auto">
                      {formatarData(item.data)}
                      {item.data_fim && item.data_fim !== item.data && ` a ${formatarData(item.data_fim)}`}
                      {item.hora_inicio && ` · ${item.hora_inicio}–${item.hora_fim}`}
                      {` · ${item.local}`}
                    </small>
                  </ListGroup.Item>
                ))}
              </ListGroup>
            )}
          </>
        )}
      </Card.Body>
    </Card>
  );
}
