"""Montagem dos dados da página inicial (T03 Atleta / T04 Diretor)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from avisos.models import Aviso, AvisoLeitura
from calendario.models import Evento, Presenca
from competicoes.models import Campeonato
from partidas.models import Partida

DIAS_PROXIMOS_EVENTOS = 30
MAX_PROXIMOS_EVENTOS = 5


def _resumo_autor(atleta):
    return {"id": atleta.id, "nome": atleta.nome, "nusp": atleta.nusp}


def avisos_fixados(usuario, hoje):
    """Avisos fixados e vigentes (UC06: expirados e excluídos não aparecem), com a marcação de lido."""
    lido = AvisoLeitura.objects.filter(aviso=OuterRef("pk"), atleta=usuario)
    qs = (
        Aviso.objects.filter(fixado=True, excluido=False)
        .filter(Q(data_expiracao__isnull=True) | Q(data_expiracao__gte=hoje))
        .select_related("autor")
        .annotate(lido=Exists(lido))
        .order_by("-data_publicacao")
    )
    return [
        {
            "id": a.id, "titulo": a.titulo, "trecho": a.conteudo[:200], "categoria": a.categoria,
            "fixado": a.fixado, "autor": _resumo_autor(a.autor), "data_publicacao": a.data_publicacao,
            "data_expiracao": a.data_expiracao, "lido": a.lido,
        }
        for a in qs
    ]


def proximos_eventos(usuario, hoje):
    """Treinos/atividades agendados e campeonatos que começam nos próximos 30 dias (até 5 itens)."""
    limite = hoje + timedelta(days=DIAS_PROXIMOS_EVENTOS)
    presente = Presenca.objects.filter(evento=OuterRef("pk"), atleta=usuario)
    eventos = (
        Evento.objects.filter(status=Evento.Status.AGENDADO, data_evento__range=(hoje, limite))
        .annotate(presente=Exists(presente))
        .order_by("data_evento", "hora_inicio")[:MAX_PROXIMOS_EVENTOS]
    )
    campeonatos = (
        Campeonato.objects.exclude(status=Campeonato.Status.CANCELADO)
        .filter(data_inicio__range=(hoje, limite))
        .order_by("data_inicio")[:MAX_PROXIMOS_EVENTOS]
    )
    itens = [
        {
            "tipo": e.tipo, "id": e.id, "titulo": e.titulo, "data": e.data_evento,
            "hora_inicio": e.hora_inicio.strftime("%H:%M"), "hora_fim": e.hora_fim.strftime("%H:%M"),
            "local": e.local_evento, "status": e.status, "presente": e.presente,
        }
        for e in eventos
    ] + [
        {
            "tipo": "campeonato", "id": c.id, "titulo": c.nome, "data": c.data_inicio, "data_fim": c.data_fim,
            "local": c.local_campeonato, "status": c.status,
        }
        for c in campeonatos
    ]
    itens.sort(key=lambda item: (item["data"], item.get("hora_inicio", "00:00")))
    return itens[:MAX_PROXIMOS_EVENTOS]


def montar_painel(usuario):
    hoje = timezone.localdate()
    painel = {
        "avisos_fixados": avisos_fixados(usuario, hoje),
        "proximos_eventos": proximos_eventos(usuario, hoje),
        "partidas_pendentes": Partida.objects.filter(status=Partida.Status.PENDENTE, adversario=usuario).count(),
        "notificacoes_nao_lidas": usuario.notificacoes.filter(lida=False).count(),
        "admin": None,
    }
    if usuario.eh_diretor:
        painel["admin"] = {
            "solicitacoes_pendentes": get_user_model().objects.filter(situacao="pendente").count(),
            "partidas_contestadas": Partida.objects.filter(status=Partida.Status.CONTESTADA).count(),
        }
    return painel