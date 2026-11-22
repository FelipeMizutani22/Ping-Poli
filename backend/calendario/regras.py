"""
Janela de registro de presença (05_REGRAS_DE_NEGOCIO §4 Calendário e presença · UC09-c).
Abre 30 min antes de hora_inicio e fecha 60 min depois de hora_fim, no mesmo dia, pelo horário do servidor.
"""
from datetime import datetime, time, timedelta

from django.utils import timezone

JANELA_ANTES_MIN = 30
JANELA_DEPOIS_MIN = 60


def janela(evento):
    """(início, fim) da janela como datetimes locais, sem sair do dia do evento."""
    tz = timezone.get_current_timezone()
    dia = evento.data_evento
    comeco_do_dia = datetime.combine(dia, time.min, tzinfo=tz)
    fim_do_dia = datetime.combine(dia, time(23, 59, 59), tzinfo=tz)
    inicio = datetime.combine(dia, evento.hora_inicio, tzinfo=tz) - timedelta(minutes=JANELA_ANTES_MIN)
    fim = datetime.combine(dia, evento.hora_fim, tzinfo=tz) + timedelta(minutes=JANELA_DEPOIS_MIN)
    return max(inicio, comeco_do_dia), min(fim, fim_do_dia)


def dentro_da_janela(evento, agora=None):
    inicio, fim = janela(evento)
    agora = timezone.localtime(agora or timezone.now())
    return inicio <= agora <= fim


def mensagem_fora_da_janela(evento):
    inicio, fim = janela(evento)
    return (f"O registro de presença para este treino está disponível das {inicio:%H:%M} às {fim:%H:%M}. "
            "Para ajustes fora desse horário, procure a Diretoria")
