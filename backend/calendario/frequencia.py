"""
Relatório de frequência (UC11 · C10).
Treino realizado = treino Agendado que já terminou (o cancelado não conta, UC07-b).
Frequência = presenças ÷ treinos realizados no período; sem treinos, o percentual não é calculado (UC11-d).
"""
import calendar
from datetime import date

from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date

from .models import Evento, Presenca
from .servicos import ajustavel

MAX_MESES = 12
MSG_PERIODO_INVERTIDO = "A data final deve ser igual ou posterior à inicial"
MSG_PERIODO_LONGO = "O período não pode ultrapassar 12 meses"
MSG_MES_INVALIDO = "Use o formato AAAA-MM"
LIMITE_DESTAQUE = 50   # abaixo disso o atleta é destacado (UC11-a.3)


class PeriodoInvalido(Exception):
    def __init__(self, campo, mensagem):
        super().__init__(mensagem)
        self.campo = campo


def periodo(params, hoje):
    """`inicio` e `fim` (período personalizado, UC11-c) ou `mes` (AAAA-MM); sem nada, o mês atual."""
    if params.get("inicio") or params.get("fim"):
        inicio, fim = parse_date(params.get("inicio") or ""), parse_date(params.get("fim") or "")
        if not inicio or not fim:
            raise PeriodoInvalido("inicio" if not inicio else "fim", "Informe a data inicial e a final (AAAA-MM-DD)")
    else:
        mes = params.get("mes") or hoje.strftime("%Y-%m")
        try:
            ano, m = (int(x) for x in mes.split("-"))
            inicio = date(ano, m, 1)
        except ValueError:
            raise PeriodoInvalido("mes", MSG_MES_INVALIDO)
        fim = date(ano, m, calendar.monthrange(ano, m)[1])
    if fim < inicio:
        raise PeriodoInvalido("fim", MSG_PERIODO_INVERTIDO)
    if (fim.year - inicio.year) * 12 + (fim.month - inicio.month) >= MAX_MESES:
        raise PeriodoInvalido("fim", MSG_PERIODO_LONGO)
    return inicio, fim


def treinos_realizados(inicio, fim):
    treinos = Evento.objects.filter(
        tipo=Evento.Tipo.TREINO, status=Evento.Status.AGENDADO, data_evento__range=(inicio, fim)
    ).order_by("data_evento", "hora_inicio")
    return [t for t in treinos if ajustavel(t)]


def percentual(presencas, total):
    return round(100 * presencas / total, 1) if total else None


def relatorio_individual(atleta, inicio, fim):
    """UC11 passo 2: cada treino realizado com presente/ausente e o autor do registro, mais o resumo."""
    treinos = treinos_realizados(inicio, fim)
    presencas = {
        p.evento_id: p
        for p in Presenca.objects.filter(atleta=atleta, evento__in=treinos).select_related("registrado_por")
    }
    linhas = [
        {
            "id": t.id, "data": t.data_evento.isoformat(), "titulo": t.titulo,
            "presente": t.id in presencas,
            "registrado_por": _resumo(presencas[t.id].registrado_por) if t.id in presencas else None,
        }
        for t in treinos
    ]
    return {
        "inicio": inicio.isoformat(), "fim": fim.isoformat(), "atleta": _resumo(atleta),
        "treinos": linhas, "total_treinos": len(treinos), "presencas": len(presencas),
        "percentual": percentual(len(presencas), len(treinos)),
    }


def relatorio_equipe(inicio, fim):
    """UC11-a: matriz atletas ativos × treinos realizados, com total e percentual de cada atleta."""
    treinos = treinos_realizados(inicio, fim)
    presentes_por_atleta = {}
    for atleta_id, evento_id in Presenca.objects.filter(evento__in=treinos).values_list("atleta_id", "evento_id"):
        presentes_por_atleta.setdefault(atleta_id, []).append(evento_id)
    atletas = get_user_model().objects.filter(situacao="ativa").select_related("curso").order_by("nome")
    return {
        "inicio": inicio.isoformat(), "fim": fim.isoformat(),
        "treinos": [{"id": t.id, "data": t.data_evento.isoformat(), "titulo": t.titulo} for t in treinos],
        "atletas": [
            {
                "atleta": _resumo(a), "curso": {"id": a.curso_id, "nome": a.curso.nome},
                "presencas": sorted(presentes_por_atleta.get(a.id, [])),
                "total": len(presentes_por_atleta.get(a.id, [])),
                "percentual": percentual(len(presentes_por_atleta.get(a.id, [])), len(treinos)),
            }
            for a in atletas
        ],
    }


def _resumo(atleta):
    return {"id": atleta.id, "nome": atleta.nome, "nusp": atleta.nusp}
