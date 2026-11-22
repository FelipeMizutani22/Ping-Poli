import { useState } from "react";
import { Alert, Button, Form, Modal } from "react-bootstrap";

import { moderarPartida } from "../../api/partidas";
import ErroCampo from "../../components/ErroCampo";
import PlacarSets from "../../components/PlacarSets";
import { linhasDeSets, setsDasLinhas } from "../../utils/partidas";
import EntradaPlacar from "./EntradaPlacar";
import ErrosPlacar from "./ErrosPlacar";

const TITULOS = {
  manter: "Manter placar registrado",
  aceitar_proposto: "Aceitar placar proposto",
  editar: "Editar placar",
  remover: "Remover partida",
};

// UC17 · Decisão do Diretor + motivo (10 a 300). Em "editar", corrige o placar com as regras do UC15.
export default function ModalModerar({ partida, decisao, onFechar, onModerada }) {
  const [motivo, setMotivo] = useState("");
  const [linhas, setLinhas] = useState(() => linhasDeSets(partida.sets, partida.formato));
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
    const corpo = { decisao, motivo: motivo.trim() };
    if (decisao === "editar") {
      const r = setsDasLinhas(linhas);
      if (r.erro) {
        setErro({ campos: { sets: [r.erro] } });
        return;
      }
      corpo.dados = {
        data_jogo: partida.data_jogo,
        campeonato: partida.competicao.campeonato_id,
        categoria: partida.categoria?.id ?? null,
        fase: partida.fase,
        tipo_adversario: partida.tipo_adversario,
        adversario: partida.adversario?.id ?? null,
        adversario_externo: partida.adversario_externo?.id ?? null,
        formato: partida.formato,
        sets: r.sets,
        observacoes: partida.observacoes,
      };
    }
    setEnviando(true);
    try {
      await moderarPartida(partida.id, corpo);
      onModerada(decisao === "remover" ? "Partida removida" : "Partida moderada");
    } catch (falha) {
      setErro(falha);
    } finally {
      setEnviando(false);
    }
  }

  const errosSets = erro?.campos?.sets || erro?.campos?.dados?.sets;
  const tamanho = motivo.trim().length;
  const nomeAdversario = partida.adversario?.nome || partida.adversario_externo?.nome;

  return (
    <Modal show onHide={onFechar} size={decisao === "editar" ? "lg" : undefined}>
      <Modal.Header closeButton>
        <Modal.Title>{TITULOS[decisao]}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="mb-2">{partida.atleta.nome} × {nomeAdversario}</p>
        {decisao === "aceitar_proposto" && (
          <p className="small">Novo placar: <PlacarSets sets={partida.contestacao.sets_propostos} /></p>
        )}
        {decisao === "remover" && (
          <Alert variant="warning" className="py-2">A partida sai das estatísticas. O registro fica no histórico.</Alert>
        )}
        {decisao === "editar" && (
          <>
            <EntradaPlacar linhas={linhas} onChange={setLinhas} rotuloAtleta={partida.atleta.nome} rotuloAdversario={nomeAdversario} />
            <ErrosPlacar mensagens={errosSets} />
          </>
        )}
        {erro?.message && !erro.campos?.motivo && !errosSets && <Alert variant="danger">{erro.message}</Alert>}
        <Form.Group controlId="motivo" className="mt-3">
          <Form.Label>Motivo da decisão *</Form.Label>
          <Form.Control as="textarea" rows={2} maxLength={300} value={motivo}
            isInvalid={Boolean(erro?.campos?.motivo)} onChange={(e) => setMotivo(e.target.value)} />
          <Form.Text className="text-muted">{tamanho}/300 caracteres (mínimo 10). Os dois jogadores recebem o motivo.</Form.Text>
          <ErroCampo erro={erro} campo="motivo" />
        </Form.Group>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={onFechar}>Cancelar</Button>
        <Button variant={decisao === "remover" ? "danger" : "primary"} onClick={enviar} disabled={enviando || tamanho < 10}>
          {enviando ? "Salvando..." : decisao === "remover" ? "Remover" : "Salvar e confirmar"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
