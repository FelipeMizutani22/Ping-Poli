"""
Modelos do app calendario: Evento e Presenca.
Correspondem às tabelas "evento" e "presenca" do diagrama ER.
"""
from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Evento(models.Model):
    class Tipo(models.TextChoices):
        TREINO = "treino", "Treino"
        ATIVIDADE = "atividade", "Atividade"

    class Status(models.TextChoices):
        AGENDADO = "agendado", "Agendado"
        CANCELADO = "cancelado", "Cancelado"

    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    titulo = models.CharField("título", max_length=100)
    data_evento = models.DateField("data")
    hora_inicio = models.TimeField("início")
    hora_fim = models.TimeField("término")
    local_evento = models.CharField("local", max_length=100)
    descricao = models.CharField("descrição", max_length=1000, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AGENDADO)
    serie_id = models.PositiveIntegerField("série", null=True, blank=True)
    motivo_cancelamento = models.CharField("motivo do cancelamento", max_length=200, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="eventos_criados"
    )
    presentes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Presenca",
        through_fields=("evento", "atleta"),
        related_name="eventos_presentes",
        blank=True,
    )

    class Meta:
        db_table = "evento"
        ordering = ["data_evento", "hora_inicio"]
        constraints = [
            models.CheckConstraint(condition=Q(hora_fim__gt=F("hora_inicio")), name="evento_horario_valido"),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.data_evento:%d/%m/%Y})"


class Presenca(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="presencas")
    atleta = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="presencas")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="presencas_registradas"
    )
    data_registro = models.DateTimeField("registrado em", default=timezone.now)

    class Meta:
        db_table = "presenca"
        constraints = [
            models.UniqueConstraint(fields=["evento", "atleta"], name="uq_presenca"),
        ]

    def __str__(self):
        return f"{self.atleta} em {self.evento}"
# Create your models here.
