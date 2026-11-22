"""Regras de negócio dos avisos (UC05, UC06 · 05_REGRAS_DE_NEGOCIO §4 Avisos)."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from nucleo.servicos import enviar_email, notificar
from .models import Aviso, AvisoLeitura

LIMITE_FIXADOS = 3
MSG_LIMITE_FIXADOS = "Já existem 3 avisos fixados. Desafixe um deles antes de continuar"


class LimiteFixadosAtingido(Exception):
    def __init__(self):
        super().__init__(MSG_LIMITE_FIXADOS)


def _verificar_limite_fixados(exceto_id=None):
    """RN17 / UC05-g: no máximo 3 fixados entre os avisos não excluídos. Trava as linhas na transação."""
    fixados = Aviso.objects.select_for_update().filter(fixado=True, excluido=False)
    if exceto_id is not None:
        fixados = fixados.exclude(pk=exceto_id)
    if len(fixados) >= LIMITE_FIXADOS:
        raise LimiteFixadosAtingido()


def _atletas_ativos():
    return get_user_model().objects.filter(situacao="ativa")


def _enviar_por_email(aviso):
    """UC05 passo 7. Falha de envio não desfaz o aviso (UC05-h): enviar_email registra no log."""
    assunto = f"[PingPoli] {aviso.titulo}"
    for atleta in _atletas_ativos():
        enviar_email(atleta.email, assunto, aviso.conteudo)


@transaction.atomic
def publicar_aviso(autor, dados):
    """UC05 fluxo básico: valida o limite de fixados, grava, notifica (urgente) e envia e-mail (opcional)."""
    notificar_email = dados.pop("notificar_email", False)
    if dados.get("fixado"):
        _verificar_limite_fixados()
    aviso = Aviso.objects.create(autor=autor, **dados)

    if aviso.categoria == Aviso.Categoria.URGENTE:
        for atleta in _atletas_ativos():
            notificar(atleta, "aviso_novo", f"Aviso urgente: {aviso.titulo}", link=f"/avisos/{aviso.id}")
    if notificar_email:
        transaction.on_commit(lambda: _enviar_por_email(aviso))
    return aviso


@transaction.atomic
def editar_aviso(aviso_id, dados):
    """UC05-a: grava as alterações e a data de edição. Reenvia o e-mail só se marcado nesta edição."""
    notificar_email = dados.pop("notificar_email", False)
    aviso = Aviso.objects.select_for_update().get(pk=aviso_id, excluido=False)
    if dados.get("fixado") and not aviso.fixado:
        _verificar_limite_fixados(exceto_id=aviso.id)
    for campo, valor in dados.items():
        setattr(aviso, campo, valor)
    aviso.data_edicao = timezone.now()
    aviso.save()
    if notificar_email:
        transaction.on_commit(lambda: _enviar_por_email(aviso))
    return aviso


@transaction.atomic
def alternar_fixado(aviso_id):
    """UC05-c: inverte fixado/não fixado, respeitando o limite de 3."""
    aviso = Aviso.objects.select_for_update().get(pk=aviso_id, excluido=False)
    if not aviso.fixado:
        _verificar_limite_fixados(exceto_id=aviso.id)
    aviso.fixado = not aviso.fixado
    aviso.save(update_fields=["fixado"])
    return aviso


def excluir_aviso(aviso):
    """UC05-b: exclusão lógica. Excluídos não contam no limite de fixados."""
    aviso.excluido = True
    aviso.save(update_fields=["excluido"])


def registrar_leitura(aviso, atleta):
    """UC06 passo 4: cria o AvisoLeitura se ainda não existir (relação n×n atleta × aviso)."""
    AvisoLeitura.objects.get_or_create(aviso=aviso, atleta=atleta)
