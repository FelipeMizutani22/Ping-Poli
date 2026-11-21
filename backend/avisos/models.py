"""
Modelos do app avisos: Aviso e AvisoLeitura.
Correspondem às tabelas "aviso" e "aviso_leitura" do diagrama ER.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Aviso(models.Model):
    class Categoria(models.TextChoices):
        GERAL = "geral", "Geral"
        TREINO = "treino", "Treino"
        CAMPEONATO = "campeonato", "Campeonato"
        URGENTE = "urgente", "Urgente"

    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="avisos")
    titulo = models.CharField("título", max_length=100)
    conteudo = models.TextField("conteúdo")
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.GERAL)
    fixado = models.BooleanField(default=False)
    data_publicacao = models.DateTimeField("data de publicação", default=timezone.now)
    data_edicao = models.DateTimeField("data de edição", null=True, blank=True)
    data_expiracao = models.DateField("data de expiração", null=True, blank=True)
    excluido = models.BooleanField("excluído", default=False)
    leitores = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="AvisoLeitura", related_name="avisos_lidos", blank=True
    )

    class Meta:
        db_table = "aviso"
        ordering = ["-fixado", "-data_publicacao"]

    def __str__(self):
        return self.titulo


class AvisoLeitura(models.Model):
    aviso = models.ForeignKey(Aviso, on_delete=models.CASCADE, related_name="leituras")
    atleta = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leituras_aviso")
    data_leitura = models.DateTimeField("data de leitura", default=timezone.now)

    class Meta:
        db_table = "aviso_leitura"
        constraints = [
            models.UniqueConstraint(fields=["aviso", "atleta"], name="uq_aviso_leitura"),
        ]

    def __str__(self):
        return f"{self.atleta} leu {self.aviso}"