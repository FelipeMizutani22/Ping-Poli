"""Regras de negócio do app partidas."""
from django.db import transaction
from django.utils import timezone

from nucleo.servicos import enviar_email, notificar, notificar_diretores
from .models import AdversarioExterno, Contestacao, Partida, SetPartida

MSG_ADVERSARIO_JA_EXISTE = "Adversário externo já cadastrado"


class AdversarioJaExiste(Exception):
    """Já existe um adversário externo com o mesmo nome (UC15-j)."""

    def __init__(self, existente):
        super().__init__(MSG_ADVERSARIO_JA_EXISTE)
        self.existente = existente


def cadastrar_adversario_externo(nome, clube=""):
    """
    Cadastra um adversário externo (UC15-a, passo 4).
    Se já existir um com o mesmo nome (sem diferenciar maiúsculas), levanta AdversarioJaExiste.
    """
    existente = AdversarioExterno.objects.filter(nome__iexact=nome).first()
    if existente is not None:
        raise AdversarioJaExiste(existente)
    return AdversarioExterno.objects.create(nome=nome, clube=clube)


@transaction.atomic
def registrar_partida(atleta, dados):
    """
    Grava uma partida já validada pelo RegistrarPartidaSerializer (UC15, passos 8 e 9).
    - Adversário Poli-USP: status pendente, e o adversário é notificado (sino + e-mail).
    - Adversário externo: já nasce confirmada (UC15-a).
    Partida e sets são gravados juntos: se algo falhar, nada fica gravado pela metade (UC15-i).
    """
    dados = dict(dados)
    sets = dados.pop("sets")
    externo = dados["tipo_adversario"] == Partida.TipoAdversario.EXTERNO

    partida = Partida.objects.create(
        atleta=atleta,
        status=Partida.Status.CONFIRMADA if externo else Partida.Status.PENDENTE,
        data_confirmacao=timezone.now() if externo else None,
        **dados,
    )
    SetPartida.objects.bulk_create(
        SetPartida(
            partida=partida, numero=numero,
            pontos_atleta=s["pontos_atleta"], pontos_adversario=s["pontos_adversario"],
        )
        for numero, s in enumerate(sets, start=1)
    )

    if not externo:
        mensagem = (
            f"{atleta.nome} registrou uma partida contra você em {partida.data_jogo:%d/%m/%Y}. "
            "Confirme ou conteste o resultado."
        )
        notificar(partida.adversario, "partida_pendente", mensagem, "/partidas/pendentes")
        # Falha no e-mail não desfaz o registro: enviar_email só registra no log (UC15-h).
        enviar_email(partida.adversario.email, "PingPoli: partida aguardando sua confirmação", mensagem)

    return partida


# ---------- Confirmar e contestar (UC16 · B5) ----------

MSG_NAO_PENDENTE = "Esta partida não está mais pendente (situação atual: {situacao})"


class PartidaNaoPendente(Exception):
    """A partida já foi confirmada, contestada ou removida (UC16-d)."""

    def __init__(self, partida):
        self.status = partida.status
        super().__init__(MSG_NAO_PENDENTE.format(situacao=partida.get_status_display().lower()))


def _travar_pendente(partida_id):
    """Relê a partida travando a linha e garante que ela continua Pendente."""
    partida = Partida.objects.select_for_update().get(pk=partida_id)
    if partida.status != Partida.Status.PENDENTE:
        raise PartidaNaoPendente(partida)
    return partida


@transaction.atomic
def confirmar_partida(partida_id, usuario):
    """UC16, passos 6 a 9: a partida passa a Confirmada e o registrante é avisado."""
    partida = _travar_pendente(partida_id)
    partida.status = Partida.Status.CONFIRMADA
    partida.data_confirmacao = timezone.now()
    partida.save(update_fields=["status", "data_confirmacao"])
    notificar(
        partida.atleta, "partida_confirmada",
        f"{usuario.nome} confirmou a partida de {partida.data_jogo:%d/%m/%Y}.",
        f"/partidas/{partida.id}",
    )
    return partida


@transaction.atomic
def contestar_partida(partida_id, usuario, justificativa, sets_propostos):
    """UC16-a: grava a contestação (e o placar proposto, se houver) e avisa o registrante e os Diretores."""
    partida = _travar_pendente(partida_id)
    contestacao = Contestacao.objects.create(partida=partida, contestante=usuario, justificativa=justificativa)
    SetPartida.objects.bulk_create(
        SetPartida(
            partida=partida, contestacao=contestacao, numero=numero,
            pontos_atleta=s["pontos_atleta"], pontos_adversario=s["pontos_adversario"],
        )
        for numero, s in enumerate(sets_propostos, start=1)
    )
    partida.status = Partida.Status.CONTESTADA
    partida.save(update_fields=["status"])

    mensagem = f"{usuario.nome} contestou a partida de {partida.data_jogo:%d/%m/%Y}."
    notificar(partida.atleta, "partida_contestada", mensagem, f"/partidas/{partida.id}")
    notificar_diretores("partida_contestada", mensagem, "/moderacao", exceto=usuario)
    return partida
