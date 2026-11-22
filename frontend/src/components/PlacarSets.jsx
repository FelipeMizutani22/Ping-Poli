// "11–7 · 9–11 · 11–5", com o vencedor de cada set em negrito (04_FRONTEND §5).
// inverter=true mostra do ponto de vista do adversário.
export default function PlacarSets({ sets = [], inverter = false }) {
  if (!sets.length) return <span className="text-muted">—</span>;
  return (
    <span className="text-nowrap">
      {sets.map((s, i) => {
        const meu = inverter ? s.pontos_adversario : s.pontos_atleta;
        const dele = inverter ? s.pontos_atleta : s.pontos_adversario;
        return (
          <span key={s.numero ?? i}>
            {i > 0 && <span className="text-muted"> · </span>}
            {meu > dele ? <strong>{meu}</strong> : meu}–{dele > meu ? <strong>{dele}</strong> : dele}
          </span>
        );
      })}
    </span>
  );
}
