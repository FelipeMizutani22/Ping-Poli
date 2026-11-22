import { useState } from "react";
import { Alert, Badge, Button, Card, Col, Form, ListGroup, Nav, Pagination, Row } from "react-bootstrap";
import { Link, useLocation } from "react-router-dom";

import { listarAvisos } from "../../api/avisos";
import AlertaErro from "../../components/AlertaErro";
import BadgeCategoriaAviso from "../../components/BadgeCategoriaAviso";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarDataHora } from "../../utils/formatacao";
import { ROTULOS } from "../../utils/rotulos";

const POR_PAGINA = 10;

// Quadro de avisos (UC06): fixados no topo, marcador "Novo", filtro por categoria e busca.
// O Diretor também vê a aba "Expirados" (UC06-b).
export default function QuadroAvisos() {
  const { ehDiretor } = useAuth();
  const location = useLocation();
  const [categoria, setCategoria] = useState("");
  const [busca, setBusca] = useState("");
  const [aba, setAba] = useState("vigentes");
  const [pagina, setPagina] = useState(1);
  const { dados: avisos, carregando, erro } = useApi(() => listarAvisos({ categoria }), [categoria]);

  // A API já devolve na ordem certa (fixados primeiro, depois os mais recentes).
  const termo = busca.trim().toLowerCase();
  const filtrados = (avisos || [])
    .filter((a) => (aba === "expirados" ? a.expirado : !a.expirado))
    .filter((a) => !termo || a.titulo.toLowerCase().includes(termo) || a.conteudo.toLowerCase().includes(termo));
  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / POR_PAGINA));
  const paginaAtual = Math.min(pagina, totalPaginas);
  const visiveis = filtrados.slice((paginaAtual - 1) * POR_PAGINA, paginaAtual * POR_PAGINA);

  function mudar(setter) {
    return (e) => {
      setter(e.target.value);
      setPagina(1);
    };
  }

  return (
    <Card>
      <Card.Body>
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h1 className="h4 mb-0">Quadro de avisos</h1>
          {ehDiretor && <Button as={Link} to="/avisos/novo">Novo aviso</Button>}
        </div>

        {location.state?.mensagem && <Alert variant="warning">{location.state.mensagem}</Alert>}

        {ehDiretor && (
          <Nav variant="tabs" activeKey={aba} className="mb-3"
            onSelect={(chave) => { setAba(chave); setPagina(1); }}>
            <Nav.Item><Nav.Link eventKey="vigentes">Vigentes</Nav.Link></Nav.Item>
            <Nav.Item><Nav.Link eventKey="expirados">Expirados</Nav.Link></Nav.Item>
          </Nav>
        )}

        <Row className="g-2 mb-3">
          <Col sm={4}>
            <Form.Select aria-label="Categoria" value={categoria} onChange={mudar(setCategoria)}>
              <option value="">Todas as categorias</option>
              {Object.entries(ROTULOS.categoriaAviso).map(([valor, nome]) => (
                <option key={valor} value={valor}>{nome}</option>
              ))}
            </Form.Select>
          </Col>
          <Col sm={8}>
            <Form.Control type="search" placeholder="Buscar no título ou no conteúdo" maxLength={50}
              value={busca} onChange={mudar(setBusca)} />
          </Col>
        </Row>

        {carregando && <Carregando />}
        <AlertaErro erro={erro} />
        {!carregando && !erro && filtrados.length === 0 && <EstadoVazio mensagem="Nenhum aviso no momento" />}

        {!carregando && visiveis.length > 0 && (
          <ListGroup>
            {visiveis.map((a) => (
              <ListGroup.Item key={a.id} action as={Link} to={`/avisos/${a.id}`}
                className={a.fixado ? "destaque-amarelo" : undefined}>
                <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
                  <BadgeCategoriaAviso categoria={a.categoria} />
                  {a.fixado && <Badge bg="light" text="dark">📌 Fixado</Badge>}
                  <span className={a.lido ? "fw-semibold" : "fw-bold"}>{a.titulo}</span>
                  {!a.lido && <Badge bg="warning" text="dark">Novo</Badge>}
                </div>
                <p className="mb-1 text-muted small">
                  {a.trecho}{a.conteudo.length > a.trecho.length && "…"}
                </p>
                <small className="text-muted">
                  {a.autor.nome} · {formatarDataHora(a.data_publicacao)}
                </small>
              </ListGroup.Item>
            ))}
          </ListGroup>
        )}

        {totalPaginas > 1 && (
          <Pagination className="justify-content-center mt-3 mb-0">
            {Array.from({ length: totalPaginas }, (_, i) => i + 1).map((n) => (
              <Pagination.Item key={n} active={n === paginaAtual} onClick={() => setPagina(n)}>{n}</Pagination.Item>
            ))}
          </Pagination>
        )}
      </Card.Body>
    </Card>
  );
}
