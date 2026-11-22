import { useState } from "react";
import { Alert, Badge, Button, Card, Col, Form, Nav, Pagination, Row, Table } from "react-bootstrap";

import {
  aprovarAtleta, inativarAtleta, listarAtletas, mudarPapel, reativarAtleta, recusarAtleta,
} from "../../api/contas";
import AlertaErro from "../../components/AlertaErro";
import BadgeStatus from "../../components/BadgeStatus";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import { useAuth } from "../../contexts/AuthContext";
import { useApi } from "../../hooks/useApi";
import { formatarData, formatarDataHora } from "../../utils/formatacao";
import { ROTULOS, rotulo } from "../../utils/rotulos";
import ModalConfirmacao from "./ModalConfirmacao";

const POR_PAGINA = 20;

// UC03 · Gerenciar Atletas (Diretor): abas "Solicitações pendentes" e "Membros".
export default function GestaoAtletas() {
  const [aba, setAba] = useState("pendentes");
  const [mensagem, setMensagem] = useState(null);
  const [modal, setModal] = useState(null); // { titulo, texto, campo, textoBotao, variante, acao }
  const [versao, setVersao] = useState(0); // muda depois de cada ação → as listas recarregam

  function concluir(texto) {
    setModal(null);
    setMensagem(texto);
    setVersao((v) => v + 1);
  }

  return (
    <Card>
      <Card.Body>
        <h1 className="h4 mb-3">Atletas</h1>
        {mensagem && <Alert variant="success" dismissible onClose={() => setMensagem(null)}>{mensagem}</Alert>}

        <Nav variant="tabs" activeKey={aba} onSelect={setAba} className="mb-3">
          <Nav.Item><Nav.Link eventKey="pendentes">Solicitações pendentes</Nav.Link></Nav.Item>
          <Nav.Item><Nav.Link eventKey="membros">Membros</Nav.Link></Nav.Item>
        </Nav>

        {aba === "pendentes"
          ? <SolicitacoesPendentes versao={versao} abrirModal={setModal} concluir={concluir} />
          : <Membros versao={versao} abrirModal={setModal} />}
      </Card.Body>

      {modal && (
        <ModalConfirmacao {...modal} onFechar={() => setModal(null)}
          onConfirmar={async (texto) => concluir(await modal.acao(texto))} />
      )}
    </Card>
  );
}

function SolicitacoesPendentes({ versao, abrirModal, concluir }) {
  const { dados, carregando, erro } = useApi(() => listarAtletas({ situacao: "pendente" }), [versao]);
  const [erroAcao, setErroAcao] = useState(null);
  const solicitacoes = dados?.results || [];

  async function aprovar(atleta) {
    setErroAcao(null);
    try {
      await aprovarAtleta(atleta.id);
      concluir(`Cadastro de ${atleta.nome} aprovado.`);
    } catch (falha) {
      setErroAcao(falha);
    }
  }

  function recusar(atleta) {
    abrirModal({
      titulo: "Recusar solicitação",
      texto: `Recusar o cadastro de ${atleta.nome}? O motivo será enviado por e-mail.`,
      campo: { rotulo: "Motivo da recusa", obrigatorio: true, max: 300 },
      textoBotao: "Recusar",
      variante: "danger",
      acao: async (motivo) => {
        await recusarAtleta(atleta.id, motivo);
        return `Solicitação de ${atleta.nome} recusada.`;
      },
    });
  }

  if (carregando) return <Carregando />;
  if (erro) return <AlertaErro erro={erro} />;
  if (solicitacoes.length === 0) return <EstadoVazio mensagem="Nenhuma solicitação de cadastro pendente." />;

  return (
    <>
      <AlertaErro erro={erroAcao} />
      <Table responsive hover className="align-middle">
        <thead>
          <tr>
            <th>Nome</th><th>NUSP</th><th>E-mail</th><th>Curso</th><th>Ingresso</th><th>Solicitado em</th><th />
          </tr>
        </thead>
        <tbody>
          {solicitacoes.map((a) => (
            <tr key={a.id}>
              <td className="fw-semibold">{a.nome}</td>
              <td>{a.nusp}</td>
              <td>{a.email}</td>
              <td>{a.curso.nome}</td>
              <td>{a.ano_ingresso}</td>
              <td>{formatarData(a.data_solicitacao)}</td>
              <td className="text-end text-nowrap">
                <Button size="sm" variant="success" className="me-2" onClick={() => aprovar(a)}>Aprovar</Button>
                <Button size="sm" variant="outline-danger" onClick={() => recusar(a)}>Recusar</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </>
  );
}

function Membros({ versao, abrirModal }) {
  const { usuario, recarregarUsuario } = useAuth();
  const [filtros, setFiltros] = useState({ busca: "", papel: "", situacao: "" });
  const [buscaDigitada, setBuscaDigitada] = useState("");
  const [pagina, setPagina] = useState(1);
  const { dados, carregando, erro } = useApi(
    () => listarAtletas({ ...filtros, page: pagina }),
    [filtros, pagina, versao],
  );
  const membros = dados?.results || [];
  const totalPaginas = Math.max(1, Math.ceil((dados?.count || 0) / POR_PAGINA));

  function filtrar(campo, valor) {
    setFiltros((f) => ({ ...f, [campo]: valor }));
    setPagina(1);
  }

  function confirmar(atleta, tipo) {
    const ehVoce = atleta.id === usuario.id;
    const opcoes = {
      inativar: {
        titulo: "Inativar conta",
        texto: ehVoce
          ? "Você está inativando a sua própria conta: será desconectado(a) e não conseguirá entrar de novo."
          : `${atleta.nome} não conseguirá mais entrar no sistema até ser reativado(a).`,
        campo: { rotulo: "Justificativa (opcional)", obrigatorio: false, max: 300 },
        textoBotao: "Inativar", variante: "danger",
        acao: async (just) => { await inativarAtleta(atleta.id, just); return `Conta de ${atleta.nome} inativada.`; },
      },
      reativar: {
        titulo: "Reativar conta", texto: `Reativar a conta de ${atleta.nome}?`, textoBotao: "Reativar",
        acao: async () => { await reativarAtleta(atleta.id); return `Conta de ${atleta.nome} reativada.`; },
      },
      promover: {
        titulo: "Conceder perfil de Diretor",
        texto: `${atleta.nome} passará a ter acesso às funções administrativas.`, textoBotao: "Tornar Diretor",
        acao: async () => { await mudarPapel(atleta.id, "diretor"); return `${atleta.nome} agora é Diretor(a).`; },
      },
      revogar: {
        titulo: "Revogar perfil de Diretor",
        texto: ehVoce
          ? "Você está revogando o seu próprio perfil de Diretor e perderá o acesso às funções administrativas."
          : `${atleta.nome} voltará a ser Atleta.`,
        textoBotao: "Revogar", variante: "warning",
        acao: async () => {
          await mudarPapel(atleta.id, "atleta");
          // Se revogou o próprio perfil, atualiza os dados do login: o menu e as rotas de Diretor somem na hora.
          if (ehVoce) await recarregarUsuario();
          return `${atleta.nome} voltou a ser Atleta.`;
        },
      },
    };
    abrirModal(opcoes[tipo]);
  }


  return (
    <>
      <Form onSubmit={(e) => { e.preventDefault(); filtrar("busca", buscaDigitada.trim()); }}>
        <Row className="g-2 mb-3">
          <Col md={5}>
            <Form.Control type="search" placeholder="Buscar por nome ou NUSP" value={buscaDigitada}
              onChange={(e) => setBuscaDigitada(e.target.value)} />
          </Col>
          <Col md={1}><Button type="submit" variant="outline-primary" className="w-100">Buscar</Button></Col>
          <Col md={3}>
            <Form.Select aria-label="Perfil" value={filtros.papel} onChange={(e) => filtrar("papel", e.target.value)}>
              <option value="">Todos os perfis</option>
              {Object.entries(ROTULOS.papel).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </Form.Select>
          </Col>
          <Col md={3}>
            <Form.Select aria-label="Situação" value={filtros.situacao}
              onChange={(e) => filtrar("situacao", e.target.value)}>
              <option value="">Todas as situações</option>
              {Object.entries(ROTULOS.situacao).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </Form.Select>
          </Col>
        </Row>
      </Form>

      {carregando && <Carregando />}
      <AlertaErro erro={erro} />
      {!carregando && !erro && membros.length === 0 && <EstadoVazio mensagem="Nenhum atleta encontrado." />}

      {!carregando && membros.length > 0 && (
        <>
          <Table responsive hover className="align-middle">
            <thead>
              <tr><th>Nome</th><th>NUSP</th><th>Curso</th><th>Perfil</th><th>Situação</th><th>Último acesso</th><th /></tr>
            </thead>
            <tbody>
              {membros.map((a) => (
                <tr key={a.id}>
                  <td className="fw-semibold">
                    {a.nome} {a.id === usuario.id && <Badge bg="light" text="dark">você</Badge>}
                  </td>
                  <td>{a.nusp}</td>
                  <td>{a.curso.nome}</td>
                  <td>
                    {a.papel === "diretor" ? <Badge bg="primary">{rotulo("papel", a.papel)}</Badge> : rotulo("papel", a.papel)}
                  </td>
                  <td><BadgeStatus status={a.situacao} grupo="situacao" /></td>
                  <td>{a.ultimo_acesso ? formatarDataHora(a.ultimo_acesso) : "—"}</td>
                  <td className="text-end text-nowrap">
                    {a.situacao === "ativa" && (
                      <>
                        {a.papel === "atleta"
                          ? <Button size="sm" variant="outline-primary" className="me-2"
                              onClick={() => confirmar(a, "promover")}>Tornar Diretor</Button>
                          : <Button size="sm" variant="outline-warning" className="me-2"
                              onClick={() => confirmar(a, "revogar")}>Revogar Diretor</Button>}
                        <Button size="sm" variant="outline-danger" onClick={() => confirmar(a, "inativar")}>Inativar</Button>
                      </>
                    )}
                    {a.situacao === "inativa" && (
                      <Button size="sm" variant="outline-success" onClick={() => confirmar(a, "reativar")}>Reativar</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
          {totalPaginas > 1 && (
            <Pagination className="justify-content-center">
              {Array.from({ length: totalPaginas }, (_, i) => i + 1).map((n) => (
                <Pagination.Item key={n} active={n === pagina} onClick={() => setPagina(n)}>{n}</Pagination.Item>
              ))}
            </Pagination>
          )}
        </>
      )}
    </>
  );
}