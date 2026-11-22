export default function EstadoVazio({ mensagem, acao }) {
  return (
    <div className="text-center text-muted py-5">
      <p className="mb-3">{mensagem}</p>
      {acao}
    </div>
  );
}
