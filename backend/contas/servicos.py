"""Regras de negócio do app contas."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from nucleo.servicos import enviar_email, notificar_diretores

from .models import Atleta

MSG_CONTA_EXISTENTE = (
    "Já existe uma conta com este e-mail/NUSP. Use 'Esqueci minha senha' ou procure a Diretoria"
)
MSG_SOLICITACAO_PENDENTE = "Já existe uma solicitação aguardando aprovação"
MSG_SOLICITACAO_ENVIADA = (
    "Solicitação enviada! Você receberá um e-mail quando a Diretoria avaliar seu cadastro"
)


class ConflitoCadastro(Exception):
    """E-mail ou NUSP já usado por outra conta (UC02 f, g)."""

    def __init__(self, codigo, mensagem):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


@transaction.atomic
def solicitar_cadastro(dados):
    """
    Cria a conta como Pendente (UC02) ou, se o e-mail/NUSP for de uma conta Recusada,
    reaproveita essa conta e a devolve para Pendente (UC02-b).
    Devolve (atleta, emails_enviados).
    """
    existentes = list(Atleta.objects.select_for_update().filter(Q(email=dados["email"]) | Q(nusp=dados["nusp"])))

    if any(a.situacao in (Atleta.Situacao.ATIVA, Atleta.Situacao.INATIVA) for a in existentes):
        raise ConflitoCadastro("conta_existente", MSG_CONTA_EXISTENTE)
    if any(a.situacao == Atleta.Situacao.PENDENTE for a in existentes):
        raise ConflitoCadastro("solicitacao_pendente", MSG_SOLICITACAO_PENDENTE)
    if len(existentes) > 1:  # e-mail de uma conta recusada e NUSP de outra
        raise ConflitoCadastro("conta_existente", MSG_CONTA_EXISTENTE)

    campos = {
        "nome": dados["nome"], "nusp": dados["nusp"], "email": dados["email"], "curso": dados["curso"],
        "ano_ingresso": dados["ano_ingresso"], "telefone": dados.get("telefone", ""),
    }
    if existentes:  # nova solicitação após recusa
        atleta = existentes[0]
        for campo, valor in campos.items():
            setattr(atleta, campo, valor)
        atleta.set_password(dados["senha"])
        atleta.situacao = Atleta.Situacao.PENDENTE
        atleta.motivo_recusa = ""
        atleta.avaliado_por = None
        atleta.data_avaliacao = None
        atleta.data_solicitacao = timezone.now()
        atleta.save()
    else:
        atleta = Atleta.objects.create_user(password=dados["senha"], **campos)

    notificar_diretores(
        "cadastro_pendente", f"Nova solicitação de cadastro: {atleta.nome}", link="/admin/atletas"
    )
    emails_ok = True
    for diretor in Atleta.objects.filter(papel=Atleta.Papel.DIRETOR, situacao=Atleta.Situacao.ATIVA):
        emails_ok &= enviar_email(
            diretor.email, "PingPoli: nova solicitação de cadastro",
            f"{atleta.nome} (NUSP {atleta.nusp}) solicitou cadastro na equipe. Avalie no Painel Administrativo.",
        )
    emails_ok &= enviar_email(
        atleta.email, "PingPoli: solicitação recebida",
        f"Olá, {atleta.nome}! Recebemos sua solicitação de cadastro. "
        "Você receberá um e-mail quando a Diretoria avaliar.",
    )
    return atleta, emails_ok