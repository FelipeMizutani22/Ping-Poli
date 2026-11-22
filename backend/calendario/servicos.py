"""Regras de negócio do calendário e da presença (UC07, UC09 · 05_REGRAS_DE_NEGOCIO §4 Calendário)."""
from django.contrib.auth import get_user_model
from django.db import transaction

from nucleo.servicos import enviar_email, notificar
from .models import Evento, Presenca
from .regras import dentro_da_janela, mensagem_fora_da_janela

MSG_TREINO_CANCELADO = "Este treino foi cancelado"
MSG_NAO_E_TREINO = "Só é possível registrar presença em treinos"
MSG_ATLETA_INVALIDO = "Só atletas com conta ativa podem ter presença registrada"
MSG_SO_O_AUTOR = "Você só pode remover presenças que você mesmo registrou"


class ErroPresenca(Exception):
    """Erro de regra da presença, com o status HTTP e o `codigo` do contrato."""

    def __init__(self, status_http, codigo, mensagem):
        super().__init__(mensagem)
        self.status_http = status_http
        self.codigo = codigo

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


def _verificar_registro(evento):
    """UC09 passo 4: treino Agendado e horário atual dentro da janela (05_REGRAS §4)."""
    if evento.tipo != Evento.Tipo.TREINO:
        raise ErroPresenca(400, "nao_e_treino", MSG_NAO_E_TREINO)
    if evento.status == Evento.Status.CANCELADO:
        raise ErroPresenca(409, "evento_cancelado", MSG_TREINO_CANCELADO)
    if not dentro_da_janela(evento):
        raise ErroPresenca(409, "fora_da_janela", mensagem_fora_da_janela(evento))


@transaction.atomic
def registrar_presencas(evento_id, autor, atleta_ids):
    """
    UC09: grava a presença de cada atleta, com `autor` como quem registrou (n×n atleta × evento).
    Lista vazia = o próprio autor. Os já presentes são ignorados e devolvidos (UC09-e).
    Quem foi registrado por outra pessoa é notificado (UC09-a.6).
    """
    evento = Evento.objects.select_for_update().get(pk=evento_id)
    _verificar_registro(evento)

    ids = list(dict.fromkeys(atleta_ids)) or [autor.id]
    atletas = {a.id: a for a in get_user_model().objects.filter(pk__in=ids, situacao="ativa")}
    if len(atletas) != len(ids):
        raise ErroPresenca(400, "atleta_invalido", MSG_ATLETA_INVALIDO)

    ja_presentes = set(Presenca.objects.filter(evento=evento, atleta_id__in=ids).values_list("atleta_id", flat=True))
    registrados = []
    for atleta_id in ids:
        if atleta_id in ja_presentes:
            continue
        Presenca.objects.create(evento=evento, atleta=atletas[atleta_id], registrado_por=autor)
        registrados.append(atleta_id)
        if atleta_id != autor.id:
            notificar(atletas[atleta_id], "presenca_registrada",
                      f"{autor.nome} registrou sua presença em {evento.titulo} ({evento.data_evento:%d/%m/%Y})",
                      link=f"/eventos/{evento.id}")
    return registrados, [i for i in ids if i in ja_presentes]


@transaction.atomic
def remover_presenca(evento_id, atleta_id, usuario):
    """
    UC09-b: o autor do registro remove dentro da janela. O Diretor remove sempre (UC10;
    a justificativa e a auditoria do ajuste ficam para a C9).
    """
    evento = Evento.objects.select_for_update().get(pk=evento_id)
    presenca = Presenca.objects.get(evento=evento, atleta_id=atleta_id)
    if not usuario.eh_diretor:
        if presenca.registrado_por_id != usuario.id:
            raise ErroPresenca(403, "nao_e_autor", MSG_SO_O_AUTOR)
        _verificar_registro(evento)
    presenca.delete()
