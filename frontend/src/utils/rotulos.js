// Único lugar com os rótulos exibidos para cada valor de status (02_MODELO_DE_DADOS).
export const ROTULOS = {
  situacao: { pendente: "Pendente", ativa: "Ativa", recusada: "Recusada", inativa: "Inativa" },
  papel: { atleta: "Atleta", diretor: "Diretor de Modalidade" },
  categoriaAviso: { geral: "Geral", treino: "Treino", campeonato: "Campeonato", urgente: "Urgente" },
  tipoEvento: { treino: "Treino", atividade: "Atividade" },
  statusEvento: { agendado: "Agendado", cancelado: "Cancelado" },
  statusCampeonato: {
    planejado: "Planejado",
    inscricoes_abertas: "Inscrições Abertas",
    inscricoes_encerradas: "Inscrições Encerradas",
    finalizado: "Finalizado",
    cancelado: "Cancelado",
  },
  statusInscricao: { ativa: "Ativa", cancelada: "Cancelada" },
  statusPartida: { pendente: "Pendente", confirmada: "Confirmada", contestada: "Contestada", removida: "Removida" },
  tipoAdversario: { poli: "Poli-USP", externo: "Externo" },
  formato: { 3: "Melhor de 3", 5: "Melhor de 5", 7: "Melhor de 7" },
  maoDominante: { destro: "Destro", canhoto: "Canhoto" },
};

// Cor do Bootstrap por status (04_FRONTEND §6)
export const CORES_STATUS = {
  pendente: "warning",
  confirmada: "success",
  ativa: "success",
  agendado: "primary",
  inscricoes_abertas: "success",
  inscricoes_encerradas: "warning",
  planejado: "info",
  finalizado: "dark",
  contestada: "danger",
  recusada: "danger",
  removida: "secondary",
  cancelada: "secondary",
  cancelado: "secondary",
  inativa: "secondary",
};

export function rotulo(grupo, valor) {
  return ROTULOS[grupo]?.[valor] ?? valor;
}
