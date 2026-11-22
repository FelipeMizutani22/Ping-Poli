"""
Eventos de demonstração (08_DEMO_E_ENTREGA §1 · C5).
- Treinos às terças e quintas, 18h–20h, "CEPEUSP – Ginásio", das últimas 8 semanas e das próximas 4.
- Um treino HOJE que começa 30 min depois do horário do seed e dura 2 h (a janela de presença já está aberta).
- Uma atividade daqui a 10 dias.
- Presenças variadas nos treinos que já passaram (C8).
⚠ Rode `seed_demo --reset` uns 15 minutos antes da apresentação.
"""
from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Evento, Presenca

LOCAL_TREINO = "CEPEUSP – Ginásio"
DIAS_DE_TREINO = (1, 3)  # terça e quinta (segunda = 0)
SEMANAS_ANTES = 8
SEMANAS_DEPOIS = 4


def _treino_de_hoje(agora):
    """Começa 30 min depois de agora e dura 2 h, sem passar da meia-noite (CheckConstraint hora_fim > hora_inicio)."""
    hoje = agora.date()
    inicio = (agora + timedelta(minutes=30)).replace(second=0, microsecond=0)
    limite_inicio = datetime.combine(hoje, time(21, 59), tzinfo=agora.tzinfo)
    inicio = min(inicio, limite_inicio) if inicio.date() == hoje else limite_inicio
    fim = min(inicio + timedelta(hours=2), datetime.combine(hoje, time(23, 59), tzinfo=agora.tzinfo))
    return inicio.time(), fim.time()


def seed(rng, ctx):
    agora = timezone.localtime()
    hoje = agora.date()
    diretor = ctx["diretor"]

    eventos = []
    dia = hoje - timedelta(weeks=SEMANAS_ANTES)
    while dia <= hoje + timedelta(weeks=SEMANAS_DEPOIS):
        if dia.weekday() in DIAS_DE_TREINO:
            eventos.append(Evento(
                tipo="treino", titulo="Treino da equipe", data_evento=dia,
                hora_inicio=time(18, 0), hora_fim=time(20, 0), local_evento=LOCAL_TREINO,
                descricao="Treino regular: aquecimento, exercícios técnicos e jogos.", criado_por=diretor,
            ))
        dia += timedelta(days=1)

    inicio, fim = _treino_de_hoje(agora)
    eventos.append(Evento(
        tipo="treino", titulo="Treino livre", data_evento=hoje, hora_inicio=inicio, hora_fim=fim,
        local_evento=LOCAL_TREINO, descricao="Treino livre: jogos entre os atletas.", criado_por=diretor,
    ))
    eventos.append(Evento(
        tipo="atividade", titulo="Palestra sobre preparação física", data_evento=hoje + timedelta(days=10),
        hora_inicio=time(19, 0), hora_fim=time(20, 30), local_evento="CEPEUSP – Sala de reuniões",
        descricao="Conversa com o preparador físico sobre aquecimento e prevenção de lesões.", criado_por=diretor,
    ))
    Evento.objects.bulk_create(eventos)
    ctx["treino_hoje"] = Evento.objects.get(titulo="Treino livre", data_evento=hoje)
    presencas = _presencas_dos_treinos_passados(rng, ctx, hoje)
    return f"{len(eventos)} eventos, {presencas} presenças (treino de hoje às {inicio:%H:%M})"


def _presencas_dos_treinos_passados(rng, ctx, hoje):
    """
    Presenças variadas nos treinos que já aconteceram (C8). Cada atleta tem uma assiduidade própria;
    de vez em quando a presença é registrada por um colega, para mostrar o autor do registro.
    O treino de hoje fica sem presenças: a Ana confirma a dela na demo.
    """
    atletas = ctx["atletas"]
    assiduidade = {a.id: rng.uniform(0.35, 0.95) for a in atletas}
    assiduidade[ctx["ana"].id] = 0.85
    tz = timezone.get_current_timezone()
    presencas = []
    for treino in Evento.objects.filter(tipo="treino", data_evento__lt=hoje):
        presentes = [a for a in atletas if rng.random() < assiduidade[a.id]]
        for atleta in presentes:
            autor = rng.choice(presentes) if rng.random() < 0.2 else atleta
            chegada = datetime.combine(treino.data_evento, treino.hora_inicio, tzinfo=tz)
            presencas.append(Presenca(
                evento=treino, atleta=atleta, registrado_por=autor,
                data_registro=chegada + timedelta(minutes=rng.randint(-20, 40)),
            ))
    Presenca.objects.bulk_create(presencas)
    return len(presencas)
