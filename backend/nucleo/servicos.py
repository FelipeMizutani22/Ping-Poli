"""
Serviços comuns usados por todos os apps: notificações, auditoria e e-mail.
Sempre use estas funções em vez de criar Notificacao/Auditoria diretamente.
"""
import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from .models import Auditoria, Notificacao

logger = logging.getLogger(__name__)


def _para_json(valor):
    """Converte um dicionário em texto JSON (datas viram texto). None vira string vazia."""
    if valor is None:
        return ""
    return json.dumps(valor, ensure_ascii=False, default=str)


def notificar(destinatario, tipo, mensagem, link=""):
    """Cria uma notificação na página inicial (sino) de um atleta."""
    return Notificacao.objects.create(
        destinatario=destinatario, tipo=tipo, mensagem=mensagem[:300], link=link
    )


def notificar_diretores(tipo, mensagem, link="", exceto=None):
    """Notifica todos os Diretores com conta Ativa (opcionalmente menos um)."""
    diretores = get_user_model().objects.filter(papel="diretor", situacao="ativa")
    if exceto is not None:
        diretores = diretores.exclude(pk=exceto.pk)
    return [notificar(d, tipo, mensagem, link) for d in diretores]


def auditar(entidade, registro_id, acao, autor, justificativa="", anterior=None, novo=None):
    """Registra quem alterou o quê, quando e por quê."""
    return Auditoria.objects.create(
        entidade=entidade,
        registro_id=registro_id,
        acao=acao,
        autor=autor,
        justificativa=justificativa,
        valor_anterior=_para_json(anterior),
        valor_novo=_para_json(novo),
    )


def enviar_email(destinatario_email, assunto, corpo):
    """Envia e-mail sem nunca derrubar a operação: em caso de falha, registra no log e devolve False."""
    try:
        send_mail(assunto, corpo, settings.DEFAULT_FROM_EMAIL, [destinatario_email])
        return True
    except Exception:
        logger.exception("Falha ao enviar e-mail para %s", destinatario_email)
        return False