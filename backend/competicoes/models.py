"""
Modelos do app competicoes: Campeonato, Categoria e Inscricao.
Correspondem às tabelas "campeonato", "categoria" e "inscricao" do diagrama ER.
"""
from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Campeonato(models.Model):
    class Status(models.TextChoices):
        PLANEJADO = "planejado", "Planejado"
        INSCRICOES_ABERTAS = "inscricoes_abertas", "Inscrições Abertas"
        INSCRICOES_ENCERRADAS = "inscricoes_encerradas", "Inscrições Encerradas"
        FINALIZADO = "finalizado", "Finalizado"
        CANCELADO = "cancelado", "Cancelado"

    nome = models.CharField(max_length=120)
    organizador = models.CharField(max_length=100)
    local_campeonato = models.CharField("local", max_length=150)
    data_inicio = models.DateField("início")
    data_fim = models.DateField("término")
    abertura_inscricoes = models.DateTimeField("abertura das inscrições")
    encerramento_inscricoes = models.DateTimeField("encerramento das inscrições")
    valor_inscricao = models.DecimalField("valor da inscrição", max_digits=10, decimal_places=2, null=True, blank=True)
    link_regulamento = models.URLField("link do regulamento", max_length=255, blank=True)
    observacoes = models.CharField("observações", max_length=1000, blank=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PLANEJADO)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="campeonatos_criados"
    )

    class Meta:
        db_table = "campeonato"
        ordering = ["-data_inicio"]
        constraints = [
            models.CheckConstraint(condition=Q(data_fim__gte=F("data_inicio")), name="campeonato_datas_validas"),
            models.CheckConstraint(
                condition=Q(encerramento_inscricoes__gt=F("abertura_inscricoes")),
                name="campeonato_inscricoes_validas",
            ),
        ]

    def __str__(self):
        return self.nome


class Categoria(models.Model):
    campeonato = models.ForeignKey(Campeonato, on_delete=models.CASCADE, related_name="categorias")
    nome = models.CharField(max_length=50)
    vagas = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Vazio = sem limite")

    class Meta:
        db_table = "categoria"
        ordering = ["campeonato", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["campeonato", "nome"], name="uq_categoria_nome"),
        ]

    def __str__(self):
        return f"{self.campeonato} – {self.nome}"


class Inscricao(models.Model):
    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        CANCELADA = "cancelada", "Cancelada"

    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="inscricoes")
    atleta = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inscricoes")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ATIVA)
    observacoes = models.CharField("observações", max_length=300, blank=True)
    data_inscricao = models.DateTimeField("data da inscrição", default=timezone.now)
    inscrito_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inscricoes_feitas"
    )
    colocacao = models.PositiveSmallIntegerField("colocação", null=True, blank=True)
    destaque = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "inscricao"
        ordering = ["categoria", "atleta"]
        constraints = [
            models.UniqueConstraint(fields=["categoria", "atleta"], name="uq_inscricao"),
        ]

    def __str__(self):
        return f"{self.atleta} em {self.categoria}"