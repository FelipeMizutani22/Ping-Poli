// Neutraliza fórmulas ao abrir o CSV em planilhas e preserva aspas/quebras.
export function celulaCsv(valor) {
  let texto = String(valor ?? '');
  if (/^[\s]*[=+@-]/.test(texto) || /^[\t\r\n]/.test(texto)) texto = "'" + texto;
  return '"' + texto.replaceAll('"', '""') + '"';
}
export function csvInscritos(dados) {
  const linhas = [['Campeonato', 'Categoria', 'Nome', 'NUSP', 'Curso', 'Data da inscrição', 'Observações', 'Colocação', 'Destaque']];
  dados.categorias.forEach(c => c.inscricoes.forEach(i => linhas.push([dados.campeonato.nome, c.nome, i.atleta.nome, i.atleta.nusp, i.atleta.curso, i.data_inscricao, i.observacoes, i.colocacao, i.destaque])));
  return '\uFEFF' + linhas.map(l => l.map(celulaCsv).join(';')).join('\r\n');
}
