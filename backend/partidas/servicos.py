"""Regras de negócio do app partidas."""
import json

from django.db import transaction
from django.utils import timezone

from nucleo.servicos import enviar_email, notificar, notificar_diretores
from .models import AdversarioExterno, Contestacao, HistoricoPartida, Partida, SetPartida

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


# ---------- Moderação pelo Diretor (UC17 · B7) ----------

MSG_CONFLITO = "Você é um dos jogadores desta partida. A moderação deve ser feita por outro Diretor"
MSG_SEM_PROPOSTO = "A contestação não trouxe placar proposto"
MSG_DECISAO_INVALIDA = "Esta decisão não se aplica a uma partida {situacao}"
MARCA_PROPRIO_JOGADOR = "[moderada pelo próprio jogador] "

# Em que situação da partida cada decisão é permitida (05_REGRAS §1, ciclo da partida)
DECISOES_PERMITIDAS = {
    "manter": {Partida.Status.CONTESTADA},
    "aceitar_proposto": {Partida.Status.CONTESTADA},
    "editar": {Partida.Status.CONTESTADA, Partida.Status.CONFIRMADA},
    "remover": {Partida.Status.PENDENTE, Partida.Status.CONFIRMADA, Partida.Status.CONTESTADA},
}


class ModeracaoInvalida(Exception):
    def __init__(self, status_http, codigo, mensagem):
        super().__init__(mensagem)
        self.status_http = status_http
        self.codigo = codigo


def _recriar_sets_oficiais(partida, sets):
    partida.sets.filter(contestacao__isnull=True).delete()
    SetPartida.objects.bulk_create(
        SetPartida(partida=partida, numero=numero,
                   pontos_atleta=s["pontos_atleta"], pontos_adversario=s["pontos_adversario"])
        for numero, s in enumerate(sets, start=1)
    )


@transaction.atomic
def moderar_partida(partida_id, diretor, decisao, motivo, dados=None):
    """
    UC17: o Diretor mantém, aceita o placar proposto, edita ou remove uma partida.
    A versão anterior vai para o HistoricoPartida ANTES de qualquer alteração.
    `dados` (só em "editar") já vem validado pelo RegistrarPartidaSerializer.
    """
    from django.contrib.auth import get_user_model

    from .serializers import PartidaSerializer

    partida = Partida.objects.select_for_update().get(pk=partida_id)

    # 1. Conflito de interesse (UC17-l)
    proprio_jogador = diretor.id in (partida.atleta_id, partida.adversario_id)
    if proprio_jogador:
        outro_diretor = (
            get_user_model().objects.filter(papel="diretor", situacao="ativa").exclude(pk=diretor.pk).exists()
        )
        if outro_diretor:
            raise ModeracaoInvalida(403, "conflito_interesse", MSG_CONFLITO)

    # 2. A decisão vale para a situação atual da partida?
    if partida.status not in DECISOES_PERMITIDAS[decisao]:
        raise ModeracaoInvalida(
            409, "situacao_invalida", MSG_DECISAO_INVALIDA.format(situacao=partida.get_status_display().lower())
        )
    contestacao = partida.contestacoes.filter(resolvida_por__isnull=True).order_by("-data_contestacao").first()
    propostos = list(contestacao.sets_propostos.order_by("numero")) if contestacao else []
    if decisao == "aceitar_proposto" and not propostos:
        raise ModeracaoInvalida(400, "sem_placar_proposto", MSG_SEM_PROPOSTO)

    # 3. Histórico ANTES de alterar (UC17 passo 9 · "nenhuma partida é apagada fisicamente")
    HistoricoPartida.objects.create(
        partida=partida,
        alterado_por=diretor,
        motivo=((MARCA_PROPRIO_JOGADOR if proprio_jogador else "") + motivo)[:300],
        valores_anteriores=json.dumps(PartidaSerializer(partida).data, ensure_ascii=False, default=str),
    )

    # 4. Aplicar a decisão
    if decisao == "aceitar_proposto":
        _recriar_sets_oficiais(partida, [
            {"pontos_atleta": s.pontos_atleta, "pontos_adversario": s.pontos_adversario} for s in propostos
        ])
    elif decisao == "editar":
        dados = dict(dados)
        sets = dados.pop("sets")
        for campo, valor in dados.items():
            setattr(partida, campo, valor)
        _recriar_sets_oficiais(partida, sets)

    if decisao == "remover":
        partida.status = Partida.Status.REMOVIDA
    else:
        partida.status = Partida.Status.CONFIRMADA
        partida.data_confirmacao = partida.data_confirmacao or timezone.now()
    partida.save()

    # 5. Fechar a contestação e avisar os dois jogadores
    if contestacao is not None:
        contestacao.resolvida_por = diretor
        contestacao.motivo_decisao = motivo
        contestacao.data_resolucao = timezone.now()
        contestacao.save(update_fields=["resolvida_por", "motivo_decisao", "data_resolucao"])

    removida = decisao == "remover"
    mensagem = (
        f"A Diretoria {'removeu' if removida else 'moderou'} a partida de {partida.data_jogo:%d/%m/%Y}. "
        f"Motivo: {motivo}"
    )
    for jogador in (partida.atleta, partida.adversario):
        if jogador is not None:
            notificar(jogador, "partida_removida" if removida else "partida_moderada", mensagem,
                      f"/partidas/{partida.id}")
    return partida
