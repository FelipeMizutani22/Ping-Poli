// Ajuda a mostrar uma partida do ponto de vista de quem está logado.
// A API guarda tudo do ponto de vista do registrante ("atleta"); se eu sou o adversário, o placar é invertido.
export function perspectiva(partida, usuarioId) {
  const souAdversario = partida.adversario?.id === usuarioId;
  const oponente = souAdversario
    ? partida.atleta
    : partida.adversario || partida.adversario_externo;
  const setsPro = souAdversario ? partida.placar_sets.adversario : partida.placar_sets.atleta;
  const setsContra = souAdversario ? partida.placar_sets.atleta : partida.placar_sets.adversario;
  return {
    souAdversario,
    oponente,
    oponenteNome: oponente ? oponente.nome + (oponente.clube ? ` (${oponente.clube})` : "") : "—",
    setsPro,
    setsContra,
    venceu: setsPro > setsContra,
  };
}

// Conversões entre as linhas do formulário de placar e o formato da API
export function linhasVazias(formato) {
  return Array.from({ length: Number(formato) }, () => ({ pontos_atleta: "", pontos_adversario: "" }));
}

export function linhasDeSets(sets, formato) {
  const linhas = linhasVazias(formato);
  sets.forEach((s, i) => {
    if (i < linhas.length) linhas[i] = { pontos_atleta: String(s.pontos_atleta), pontos_adversario: String(s.pontos_adversario) };
  });
  return linhas;
}

// Devolve { sets, erro }. Linhas totalmente vazias são ignoradas (o formato limita o máximo, não o mínimo).
export function setsDasLinhas(linhas) {
  const sets = [];
  for (let i = 0; i < linhas.length; i++) {
    const { pontos_atleta: a, pontos_adversario: b } = linhas[i];
    if (a === "" && b === "") continue;
    if (a === "" || b === "") return { sets, erro: `Set ${i + 1}: informe os pontos dos dois jogadores` };
    sets.push({ pontos_atleta: Number(a), pontos_adversario: Number(b) });
  }
  return { sets, erro: null };
}
