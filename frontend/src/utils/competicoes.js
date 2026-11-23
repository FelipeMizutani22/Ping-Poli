export function mensagensErro(valor) {
  if (!valor) return [];
  if (typeof valor === 'string') return [valor];
  return Object.values(valor).flatMap(mensagensErro);
}

export function horarioBrasilia(valor) {
  if (!valor) return '';
  const partes = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(valor)).map((p) => [p.type, p.value]));
  return `${partes.year}-${partes.month}-${partes.day}T${partes.hour}:${partes.minute}:${partes.second}`;
}

export function exibirHorario(valor) {
  return valor ? new Date(valor).toLocaleString('pt-BR', {
    timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short',
  }) : '';
}

export function valorInscricao(valor) {
  return valor === null || valor === '' ? 'Não informado' : Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function linkSeguro(valor) {
  try { const url = new URL(valor); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; }
  catch { return null; }
}

export function prepararCampeonato(form) {
  return {
    ...form, nome: form.nome.trim(), organizador: form.organizador.trim(), local_campeonato: form.local_campeonato.trim(),
    abertura_inscricoes: `${form.abertura_inscricoes}-03:00`,
    encerramento_inscricoes: `${form.encerramento_inscricoes}-03:00`,
    valor_inscricao: form.valor_inscricao === '' ? null : form.valor_inscricao,
    categorias: form.categorias.map((c) => ({ ...(c.id ? { id: c.id } : {}), nome: c.nome.trim(), vagas: c.vagas === '' ? null : Number(c.vagas) })),
  };
}
