"""Regras de negócio do app contas."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.authtoken.models import Token

from nucleo.servicos import auditar, enviar_email, notificar, notificar_diretores
from .models import Atleta, Curso

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



class SituacaoInvalida(Exception):
    """A ação não é permitida na situação atual da conta."""


def _avaliar(atleta_id, diretor, nova_situacao, motivo=""):
    atleta = Atleta.objects.select_for_update().get(pk=atleta_id)
    if atleta.situacao != Atleta.Situacao.PENDENTE:
        raise SituacaoInvalida(f"Esta solicitação não está mais pendente (situação atual: {atleta.get_situacao_display()}).")
    anterior = {"situacao": atleta.situacao}
    atleta.situacao = nova_situacao
    atleta.motivo_recusa = motivo
    atleta.avaliado_por = diretor
    atleta.data_avaliacao = timezone.now()
    atleta.save()
    acao = "aprovar" if nova_situacao == Atleta.Situacao.ATIVA else "recusar"
    auditar("atleta", atleta.pk, acao, diretor, motivo, anterior=anterior, novo={"situacao": nova_situacao})
    return atleta


@transaction.atomic
def aprovar_cadastro(atleta_id, diretor):
    """UC03: Pendente → Ativa. Notifica e avisa o atleta por e-mail."""
    atleta = _avaliar(atleta_id, diretor, Atleta.Situacao.ATIVA)
    notificar(atleta, "cadastro_aprovado", "Bem-vindo(a) à equipe! Seu cadastro foi aprovado.", link="/")
    enviar_email(atleta.email, "PingPoli: cadastro aprovado",
                 f"Olá, {atleta.nome}! Seu cadastro foi aprovado. Você já pode entrar no PingPoli.")
    return atleta


@transaction.atomic
def recusar_cadastro(atleta_id, diretor, motivo):
    """UC03: Pendente → Recusada, com motivo. Avisa o solicitante por e-mail."""
    atleta = _avaliar(atleta_id, diretor, Atleta.Situacao.RECUSADA, motivo)
    enviar_email(atleta.email, "PingPoli: solicitação de cadastro",
                 f"Olá, {atleta.nome}. Sua solicitação não foi aprovada. Motivo: {motivo}")
    return atleta


# --- Inativar, reativar e mudar papel (UC03) --------------------------------

MSG_ULTIMO_DIRETOR = "A equipe precisa de pelo menos um Diretor ativo."


class UltimoDiretor(Exception):
    """A ação deixaria a equipe sem nenhum Diretor ativo."""


def _ha_outro_diretor_ativo(atleta):
    return (
        Atleta.objects.filter(papel=Atleta.Papel.DIRETOR, situacao=Atleta.Situacao.ATIVA)
        .exclude(pk=atleta.pk)
        .exists()
    )


@transaction.atomic
def mudar_situacao(atleta_id, diretor, nova_situacao, justificativa=""):
    """Ativa → Inativa ou Inativa → Ativa. Inativar também encerra as sessões (apaga o token)."""
    origem = {Atleta.Situacao.INATIVA: Atleta.Situacao.ATIVA, Atleta.Situacao.ATIVA: Atleta.Situacao.INATIVA}
    atleta = Atleta.objects.select_for_update().get(pk=atleta_id)
    if atleta.situacao != origem[nova_situacao]:
        raise SituacaoInvalida(f"Ação não permitida para uma conta {atleta.get_situacao_display()}.")
    if nova_situacao == Atleta.Situacao.INATIVA and atleta.eh_diretor and not _ha_outro_diretor_ativo(atleta):
        raise UltimoDiretor(MSG_ULTIMO_DIRETOR)

    anterior = atleta.situacao
    atleta.situacao = nova_situacao
    atleta.save(update_fields=["situacao"])
    if nova_situacao == Atleta.Situacao.INATIVA:
        Token.objects.filter(user=atleta).delete()
    acao = "inativar" if nova_situacao == Atleta.Situacao.INATIVA else "reativar"
    auditar("atleta", atleta.pk, acao, diretor, justificativa,
            anterior={"situacao": anterior}, novo={"situacao": nova_situacao})
    return atleta


@transaction.atomic
def mudar_papel(atleta_id, diretor, novo_papel):
    """Concede ou revoga o perfil de Diretor (só para contas Ativas)."""
    atleta = Atleta.objects.select_for_update().get(pk=atleta_id)
    if atleta.situacao != Atleta.Situacao.ATIVA:
        raise SituacaoInvalida("Só é possível mudar o perfil de uma conta Ativa.")
    if atleta.papel == novo_papel:
        return atleta
    if novo_papel == Atleta.Papel.ATLETA and not _ha_outro_diretor_ativo(atleta):
        raise UltimoDiretor(MSG_ULTIMO_DIRETOR)

    anterior = atleta.papel
    atleta.papel = novo_papel
    atleta.save(update_fields=["papel"])
    auditar("atleta", atleta.pk, "mudar_papel", diretor, anterior={"papel": anterior}, novo={"papel": novo_papel})
    return atleta


# --- Editar dados de um membro (UC03-b) --------------------------------------


def _para_auditoria(valor):
    return valor.nome if isinstance(valor, Curso) else valor


@transaction.atomic
def editar_atleta(atleta_id, diretor, dados):
    """Grava só o que mudou e audita os valores anterior e novo. Avisa por e-mail se o e-mail mudou."""
    atleta = Atleta.objects.select_for_update().get(pk=atleta_id)
    anterior, novo = {}, {}
    for campo, valor in dados.items():
        atual = getattr(atleta, campo)
        if atual != valor:
            anterior[campo] = _para_auditoria(atual)
            novo[campo] = _para_auditoria(valor)
            setattr(atleta, campo, valor)
    if not novo:
        return atleta

    atleta.save()
    auditar("atleta", atleta.pk, "editar", diretor, anterior=anterior, novo=novo)
    if "email" in novo:
        enviar_email(
            atleta.email, "PingPoli: e-mail de acesso alterado",
            f"Olá, {atleta.nome}. A Diretoria alterou o seu e-mail de acesso ao PingPoli para {atleta.email}.",
        )
    return atleta