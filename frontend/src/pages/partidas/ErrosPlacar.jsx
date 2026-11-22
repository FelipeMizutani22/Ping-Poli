// Lista as mensagens de placar devolvidas pela API (ex.: "Set 2: o vencedor precisa de 11 pontos com 2 de vantagem").
export default function ErrosPlacar({ mensagens }) {
  if (!mensagens?.length) return null;
  return (
    <div className="text-danger small">
      {mensagens.map((m) => (
        <div key={m}>{m}</div>
      ))}
    </div>
  );
}
