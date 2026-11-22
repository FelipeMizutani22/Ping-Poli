import { useEffect } from "react";
import { Badge, Button, Card } from "react-bootstrap";
import { Link, useNavigate, useParams } from "react-router-dom";

import { buscarAviso } from "../../api/avisos";
import AlertaErro from "../../components/AlertaErro";
import BadgeCategoriaAviso from "../../components/BadgeCategoriaAviso";
import Carregando from "../../components/Carregando";
import { useApi } from "../../hooks/useApi";
import { formatarData, formatarDataHora } from "../../utils/formatacao";

// Aviso completo (UC06 passo 4). Abrir esta tela marca o aviso como lido na API (AvisoLeitura).
export default function DetalheAviso() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { dados: aviso, carregando, erro } = useApi(() => buscarAviso(id), [id]);

  // UC06-d: aviso removido (ou expirado) enquanto era aberto → volta ao quadro com a mensagem da API.
  useEffect(() => {
    if (erro?.status === 404) navigate("/avisos", { replace: true, state: { mensagem: erro.message } });
  }, [erro, navigate]);

  if (carregando) return <Carregando />;
  if (erro) return <AlertaErro erro={erro} />;
  if (!aviso) return null;

  return (
    <Card className={aviso.fixado ? "destaque-amarelo" : undefined}>
      <Card.Body>
        <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
          <BadgeCategoriaAviso categoria={aviso.categoria} />
          {aviso.fixado && <Badge bg="light" text="dark">📌 Fixado</Badge>}
          {aviso.expirado && <Badge bg="secondary">Expirado</Badge>}
        </div>
        <h1 className="h4">{aviso.titulo}</h1>
        <p className="text-muted small mb-3">
          {aviso.autor.nome} · {formatarDataHora(aviso.data_publicacao)}
          {aviso.data_edicao && <> · editado em {formatarDataHora(aviso.data_edicao)}</>}
          {aviso.data_expiracao && <> · válido até {formatarData(aviso.data_expiracao)}</>}
        </p>
        <div style={{ whiteSpace: "pre-line" }}>{aviso.conteudo}</div>
        <Button as={Link} to="/avisos" variant="outline-primary" className="mt-4">Voltar ao quadro</Button>
      </Card.Body>
    </Card>
  );
}
