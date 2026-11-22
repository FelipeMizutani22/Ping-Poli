"""Regras de negócio do app partidas."""
from django.db import transaction
from django.utils import timezone

from nucleo.servicos import enviar_email, notificar
from .models import AdversarioExterno, Partida, SetPartida

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
