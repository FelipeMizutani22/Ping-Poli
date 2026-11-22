"""Regras de negócio do calendário (UC07 · 05_REGRAS_DE_NEGOCIO §4 Calendário)."""
from django.contrib.auth import get_user_model
from django.db import transaction

from nucleo.servicos import enviar_email, notificar
from .models import Evento

CAMPOS_QUE_AVISAM = ("data_evento", "hora_inicio", "hora_fim", "local_evento")
MSG_JA_CANCELADO = "Este evento já está cancelado"


class EventoJaCancelado(Exception):
    def __init__(self):
        super().__init__(MSG_JA_CANCELADO)


def _atletas_ativos():
    return get_user_model().objects.filter(situacao="ativa")


def _descrever(evento):
    return (f"{evento.titulo} em {evento.data_evento:%d/%m/%Y}, das {evento.hora_inicio:%H:%M} "
            f"às {evento.hora_fim:%H:%M}, local: {evento.local_evento}")


def _enviar_emails(assunto, corpo):
    """Falha de e-mail não desfaz a operação: enviar_email registra no log."""
    for atleta in _atletas_ativos():
        enviar_email(atleta.email, assunto, corpo)


def criar_evento(diretor, dados):
    """UC07 fluxo básico: grava o evento Agendado."""
    return Evento.objects.create(criado_por=diretor, **dados)


@transaction.atomic
def editar_evento(evento_id, dados):
    """UC07-a: grava as alterações; se data, horário ou local mudaram, avisa os atletas ativos por e-mail."""
    evento = Evento.objects.select_for_update().get(pk=evento_id)
    mudou = any(campo in dados and dados[campo] != getattr(evento, campo) for campo in CAMPOS_QUE_AVISAM)
    for campo, valor in dados.items():
        setattr(evento, campo, valor)
    evento.save()
    if mudou:
        transaction.on_commit(lambda: _enviar_emails(
            f"[PingPoli] Evento alterado: {evento.titulo}", f"O evento foi alterado: {_descrever(evento)}."
        ))
    return evento


@transaction.atomic
def cancelar_evento(evento_id, motivo=""):
    """UC07-b: status Cancelado (continua visível), notifica e manda e-mail aos atletas ativos."""
    evento = Evento.objects.select_for_update().get(pk=evento_id)
    if evento.status == Evento.Status.CANCELADO:
        raise EventoJaCancelado()
    evento.status = Evento.Status.CANCELADO
    evento.motivo_cancelamento = motivo
    evento.save(update_fields=["status", "motivo_cancelamento"])

    mensagem = f"Evento cancelado: {evento.titulo} ({evento.data_evento:%d/%m/%Y})"
    if motivo:
        mensagem += f". Motivo: {motivo}"
    for atleta in _atletas_ativos():
        notificar(atleta, "evento_cancelado", mensagem, link=f"/eventos/{evento.id}")
    transaction.on_commit(lambda: _enviar_emails(f"[PingPoli] {mensagem[:100]}", mensagem + "."))
    return evento
