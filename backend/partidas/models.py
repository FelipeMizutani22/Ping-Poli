"""
Modelos do app partidas: AdversarioExterno, Partida, Contestacao, SetPartida e HistoricoPartida.
Correspondem às tabelas de mesmo nome do diagrama ER.
"""
from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


def _vence_set(a, b):
    """Condição de banco: o lado `a` venceu o set (11 a no máximo 9, ou acima de 11 com exatamente 2 de vantagem)."""
    return (Q(**{a: 11}) & Q(**{f"{b}__lte": 9})) | (Q(**{f"{a}__gte": 12}) & Q(**{a: F(b) + 2}))


class AdversarioExterno(models.Model):
    nome = models.CharField(max_length=100)
    clube = models.CharField("clube/instituição", max_length=100, blank=True)

    class Meta:
        db_table = "adversario_externo"
        ordering = ["nome"]
        verbose_name = "adversário externo"
        verbose_name_plural = "adversários externos"

    def __str__(self):
        return f"{self.nome} ({self.clube})" if self.clube else self.nome


class Partida(models.Model):
    class TipoAdversario(models.TextChoices):
        POLI = "poli", "Poli-USP"
        EXTERNO = "externo", "Externo"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        CONFIRMADA = "confirmada", "Confirmada"
        CONTESTADA = "contestada", "Contestada"
        REMOVIDA = "removida", "Removida"

    class Formato(models.IntegerChoices):
        MELHOR_DE_3 = 3, "Melhor de 3"
        MELHOR_DE_5 = 5, "Melhor de 5"
        MELHOR_DE_7 = 7, "Melhor de 7"

    atleta = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="partidas_registradas"
    )
    adversario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="partidas_como_adversario",
    )
    adversario_externo = models.ForeignKey(
        AdversarioExterno, on_delete=models.PROTECT, null=True, blank=True, related_name="partidas"
    )
    tipo_adversario = models.CharField("tipo de adversário", max_length=10, choices=TipoAdversario.choices)
    campeonato = models.ForeignKey(
        "competicoes.Campeonato", on_delete=models.PROTECT, null=True, blank=True,
        related_name="partidas", help_text="Vazio = Amistoso/Treino",
    )
    categoria = models.ForeignKey(
        "competicoes.Categoria", on_delete=models.PROTECT, null=True, blank=True, related_name="partidas"
    )
    fase = models.CharField(max_length=50, blank=True)
    formato = models.PositiveSmallIntegerField(choices=Formato.choices)
    data_jogo = models.DateField("data do jogo")
    status = models.CharField(max_length=15, choices=Status.choices)
    observacoes = models.CharField("observações", max_length=300, blank=True)
    data_registro = models.DateTimeField("registrada em", default=timezone.now)
    data_confirmacao = models.DateTimeField("confirmada em", null=True, blank=True)

    class Meta:
        db_table = "partida"
        ordering = ["-data_jogo", "-id"]
        constraints = [
            models.CheckConstraint(
                name="partida_adversario_xor",
                condition=(
                    Q(tipo_adversario="poli", adversario__isnull=False, adversario_externo__isnull=True)
                    | Q(tipo_adversario="externo", adversario__isnull=True, adversario_externo__isnull=False)
                ),
            ),
            models.CheckConstraint(name="partida_nao_contra_si", condition=~Q(adversario=F("atleta"))),
            models.CheckConstraint(name="partida_formato_valido", condition=Q(formato__in=[3, 5, 7])),
        ]

    def __str__(self):
        oponente = self.adversario or self.adversario_externo
        return f"{self.atleta.nome} × {oponente} ({self.data_jogo:%d/%m/%Y})"

    def sets_oficiais(self):
        """Placar oficial: os sets que não pertencem a uma contestação."""
        return self.sets.filter(contestacao__isnull=True).order_by("numero")


class Contestacao(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name="contestacoes")
    contestante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="contestacoes")
    justificativa = models.CharField(max_length=500)
    data_contestacao = models.DateTimeField("contestada em", default=timezone.now)
    resolvida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="contestacoes_resolvidas",
    )
    motivo_decisao = models.CharField("motivo da decisão", max_length=300, blank=True)
    data_resolucao = models.DateTimeField("resolvida em", null=True, blank=True)

    class Meta:
        db_table = "contestacao"
        verbose_name = "contestação"
        verbose_name_plural = "contestações"

    def __str__(self):
        return f"Contestação da partida {self.partida_id}"


class SetPartida(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name="sets")
    contestacao = models.ForeignKey(
        Contestacao, on_delete=models.CASCADE, null=True, blank=True, related_name="sets_propostos",
        help_text="Vazio = placar oficial; preenchido = placar proposto na contestação",
    )
    numero = models.PositiveSmallIntegerField("set nº")
    pontos_atleta = models.PositiveSmallIntegerField()
    pontos_adversario = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "set_partida"
        ordering = ["partida", "contestacao", "numero"]
        constraints = [
            models.CheckConstraint(
                name="set_regra_11_pontos",
                condition=_vence_set("pontos_atleta", "pontos_adversario")
                | _vence_set("pontos_adversario", "pontos_atleta"),
            ),
            models.CheckConstraint(name="set_numero_valido", condition=Q(numero__gte=1, numero__lte=7)),
            models.CheckConstraint(
                name="set_pontos_max", condition=Q(pontos_atleta__lte=99, pontos_adversario__lte=99)
            ),
            models.UniqueConstraint(
                fields=["partida", "numero"], condition=Q(contestacao__isnull=True), name="uq_set_oficial"
            ),
            models.UniqueConstraint(
                fields=["contestacao", "numero"], condition=Q(contestacao__isnull=False), name="uq_set_proposto"
            ),
        ]

    def __str__(self):
        return f"Set {self.numero}: {self.pontos_atleta}–{self.pontos_adversario}"


class HistoricoPartida(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name="historico")
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="alteracoes_partida"
    )
    motivo = models.CharField(max_length=300)
    valores_anteriores = models.TextField("valores anteriores (JSON)")
    data_alteracao = models.DateTimeField("alterada em", default=timezone.now)

    class Meta:
        db_table = "historico_partida"
        ordering = ["-data_alteracao"]
        verbose_name = "histórico de partida"
        verbose_name_plural = "históricos de partida"

    def __str__(self):
        return f"Alteração da partida {self.partida_id} em {self.data_alteracao:%d/%m/%Y %H:%M}"