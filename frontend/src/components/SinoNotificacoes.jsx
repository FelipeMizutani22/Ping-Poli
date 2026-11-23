import { useCallback, useEffect, useState } from "react";
import { Badge, Button, NavDropdown, Spinner } from "react-bootstrap";
import { useLocation, useNavigate } from "react-router-dom";

import { listarNotificacoes, marcarNotificacaoLida, marcarTodasLidas } from "../api/nucleo";
import { formatarDataHora } from "../utils/formatacao";

const INTERVALO_MS = 60_000; // atualiza o contador a cada minuto
const MAX_ITENS = 10;

function IconeSino() {
  return (
    <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2zm.995-14.901a1 1 0 1 0-1.99 0A5.002 5.002 0 0 0 3 6c0
        1.098-.5 6-2 7h14c-1.5-1-2-5.902-2-7 0-2.42-1.72-4.44-4.005-4.901z" />
    </svg>
  );
}

// Sino da barra de navegação: contador de não lidas + as 10 notificações mais recentes.
export default function SinoNotificacoes() {
  const navigate = useNavigate();
  const location = useLocation();
  const [naoLidas, setNaoLidas] = useState(0);
  const [lista, setLista] = useState(null); // null = carregando
  const [aberto, setAberto] = useState(false);

  const atualizarContador = useCallback(() => {
    listarNotificacoes(true)
      .then((l) => setNaoLidas(l.length))
      .catch(() => {}); // o sino nunca derruba a página
  }, []);

  // Atualiza ao trocar de página e, enquanto a página fica aberta, a cada minuto.
  useEffect(() => { atualizarContador(); }, [location.pathname, atualizarContador]);
  useEffect(() => {
    const id = setInterval(atualizarContador, INTERVALO_MS);
    return () => clearInterval(id);
  }, [atualizarContador]);

  async function alternar(abrir) {
    setAberto(abrir);
    if (!abrir) return;
    setLista(null);
    try {
      setLista((await listarNotificacoes()).slice(0, MAX_ITENS));
    } catch {
      setLista([]);
    }
  }

  async function abrirNotificacao(n) {
    setAberto(false);
    if (!n.lida) {
      try { await marcarNotificacaoLida(n.id); } catch { /* segue mesmo assim */ }
    }
    atualizarContador();
    if (n.link) navigate(n.link);
  }

  async function marcarTodas() {
    try {
      await marcarTodasLidas();
      setLista((l) => (l || []).map((n) => ({ ...n, lida: true })));
      setNaoLidas(0);
    } catch { /* mantém como estava */ }
  }

  const titulo = (
    <span className="position-relative d-inline-flex align-items-center" aria-label={`${naoLidas} notificações não lidas`}>
      <IconeSino />
      {naoLidas > 0 && (
        <Badge pill bg="warning" text="dark" className="position-absolute top-0 start-100 translate-middle">
          {naoLidas > 9 ? "9+" : naoLidas}
        </Badge>
      )}
    </span>
  );

  return (
    <NavDropdown title={titulo} id="menu-notificacoes" align="end" show={aberto} onToggle={alternar}
      className="me-2">
      <div className="d-flex justify-content-between align-items-center px-3 py-1" style={{ minWidth: 340 }}>
        <span className="fw-semibold">Notificações</span>
        {naoLidas > 0 && (
          <Button variant="link" size="sm" className="p-0" onClick={marcarTodas}>Marcar todas como lidas</Button>
        )}
      </div>
      <NavDropdown.Divider />
      {lista === null && <div className="text-center py-3"><Spinner animation="border" size="sm" /></div>}
      {lista?.length === 0 && <div className="px-3 py-2 text-muted small">Nenhuma notificação.</div>}
      {lista?.map((n) => (
        <NavDropdown.Item key={n.id} onClick={() => abrirNotificacao(n)} className="py-2"
          style={{ whiteSpace: "normal", maxWidth: 380 }}>
          <div className={n.lida ? "text-muted" : "fw-semibold"}>
            {!n.lida && <span className="text-warning me-1">●</span>}
            {n.mensagem}
          </div>
          <div className="small text-muted">{formatarDataHora(n.data_criacao)}</div>
        </NavDropdown.Item>
      ))}
    </NavDropdown>
  );
}