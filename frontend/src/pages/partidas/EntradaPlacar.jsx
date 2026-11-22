import { Form, Table } from "react-bootstrap";

// Uma linha por set, limitada pelo formato (UC15). rotuloAtleta/rotuloAdversario dão nome às colunas.
export default function EntradaPlacar({ linhas, onChange, rotuloAtleta = "Você", rotuloAdversario = "Adversário" }) {
  function alterar(i, campo, valor) {
    if (valor !== "" && !/^\d{1,2}$/.test(valor)) return; // inteiros de 0 a 99
    onChange(linhas.map((l, j) => (j === i ? { ...l, [campo]: valor } : l)));
  }
  return (
    <Table size="sm" className="align-middle mb-1" style={{ maxWidth: 420 }}>
      <thead>
        <tr>
          <th style={{ width: 70 }}>Set</th>
          <th>{rotuloAtleta}</th>
          <th>{rotuloAdversario}</th>
        </tr>
      </thead>
      <tbody>
        {linhas.map((l, i) => (
          <tr key={i}>
            <td>{i + 1}º</td>
            <td>
              <Form.Control size="sm" inputMode="numeric" value={l.pontos_atleta}
                onChange={(e) => alterar(i, "pontos_atleta", e.target.value)} aria-label={`Set ${i + 1}, ${rotuloAtleta}`} />
            </td>
            <td>
              <Form.Control size="sm" inputMode="numeric" value={l.pontos_adversario}
                onChange={(e) => alterar(i, "pontos_adversario", e.target.value)} aria-label={`Set ${i + 1}, ${rotuloAdversario}`} />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
