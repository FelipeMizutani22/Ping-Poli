// Datas exibidas em dd/mm/aaaa (04_FRONTEND §7). Datas "AAAA-MM-DD" são lidas como data local.
function paraData(valor) {
  if (!valor) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(valor)) {
    const [a, m, d] = valor.split("-").map(Number);
    return new Date(a, m - 1, d);
  }
  return new Date(valor);
}

export function formatarData(valor) {
  const d = paraData(valor);
  return d ? d.toLocaleDateString("pt-BR") : "";
}

export function formatarDataHora(valor) {
  const d = paraData(valor);
  return d ? d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "";
}

export function formatarMes(valor) {
  const d = paraData(valor.length === 7 ? `${valor}-01` : valor);
  return d ? d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }) : "";
}

export function hojeISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
