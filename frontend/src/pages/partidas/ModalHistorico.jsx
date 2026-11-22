import { Modal, Table } from "react-bootstrap";

import { historicoPartida } from "../../api/partidas";
import AlertaErro from "../../components/AlertaErro";
import Carregando from "../../components/Carregando";
import EstadoVazio from "../../components/EstadoVazio";
import PlacarSets from "../../components/PlacarSets";
import { useApi } from "../../hooks/useApi";
import { formatarDataHora } from "../../utils/formatacao";
import { rotulo } from "../../utils/rotulos";

// UC17-f · Versões anteriores da partida
export default function ModalHistorico({ partida, onFechar }) {
  const { dados, carregando, erro } = useApi(() => historicoPartida(partida.id), [partida.id]);
  return (
    <Modal show onHide={onFechar} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Histórico de alterações</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {carregando && <Carregando />}
        <AlertaErro erro={erro} />
        {dados && dados.length === 0 && <EstadoVazio mensagem="Esta partida não tem alterações." />}
        {dados && dados.length > 0 && (
          <Table size="sm" responsive>
            <thead>
              <tr><th>Quando</th><th>Quem</th><th>Motivo</th><th>Antes</th></tr>
            </thead>
            <tbody>
              {dados.map((h) => (
                <tr key={h.id}>
                  <td className="text-nowrap">{formatarDataHora(h.data_alteracao)}</td>
                  <td>{h.alterado_por.nome}</td>
                  <td>{h.motivo}</td>
                  <td className="small">
                    {h.valores_anteriores?.status && rotulo("statusPartida", h.valores_anteriores.status)}
                    {h.valores_anteriores?.sets && <div><PlacarSets sets={h.valores_anteriores.sets} /></div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Modal.Body>
    </Modal>
  );
}
