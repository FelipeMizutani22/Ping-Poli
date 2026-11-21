"""
Modelos do app nucleo: Auditoria, Notificacao e ExecucaoRotina.
Correspondem às tabelas "auditoria", "notificacao" e "execucao_rotina" do diagrama ER.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Auditoria(models.Model):
    entidade = models.CharField(max_length=30)
    registro_id = models.PositiveIntegerField("id do registro")
    acao = models.CharField("ação", max_length=30)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="auditorias")
    justificativa = models.CharField(max_length=300, blank=True)
    valor_anterior = models.TextField(blank=True)
    valor_novo = models.TextField(blank=True)
    data_acao = models.DateTimeField("data", default=timezone.now)

    class Meta:
        db_table = "auditoria"
        ordering = ["-data_acao"]

    def __str__(self):
        return f"{self.acao} em {self.entidade} #{self.registro_id}"


class Notificacao(models.Model):
    class Tipo(models.TextChoices):
        CADASTRO_PENDENTE = "cadastro_pendente", "Cadastro pendente"
        CADASTRO_APROVADO = "cadastro_aprovado", "Cadastro aprovado"
        CADASTRO_RECUSADO = "cadastro_recusado", "Cadastro recusado"
        PARTIDA_PENDENTE = "partida_pendente", "Partida pendente"
        PARTIDA_CONFIRMADA = "partida_confirmada", "Partida confirmada"
        PARTIDA_CONTESTADA = "partida_contestada", "Partida contestada"
        PARTIDA_MODERADA = "partida_moderada", "Partida moderada"
        PARTIDA_REMOVIDA = "partida_removida", "Partida removida"
        PARTIDA_LEMBRETE = "partida_lembrete", "Lembrete de partida"
        PRESENCA_REGISTRADA = "presenca_registrada", "Presença registrada"
        EVENTO_CANCELADO = "evento_cancelado", "Evento cancelado"
        AVISO_NOVO = "aviso_novo", "Aviso novo"
        INSCRICOES_ABERTAS = "inscricoes_abertas", "Inscrições abertas"
        INSCRICAO_LEMBRETE = "inscricao_lembrete", "Lembrete de inscrição"
        INSCRICAO_CONFIRMADA = "inscricao_confirmada", "Inscrição confirmada"
        CAMPEONATO_FINALIZADO = "campeonato_finalizado", "Campeonato finalizado"
        ROTINA_FALHOU = "rotina_falhou", "Falha em rotina"

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    mensagem = models.CharField(max_length=300)
    link = models.CharField(max_length=255, blank=True, help_text="Rota do site, ex.: /partidas/12")
    lida = models.BooleanField(default=False)
    data_criacao = models.DateTimeField("criada em", default=timezone.now)

    class Meta:
        db_table = "notificacao"
        ordering = ["-data_criacao"]
        verbose_name = "notificação"
        verbose_name_plural = "notificações"

    def __str__(self):
        return f"Para {self.destinatario}: {self.mensagem[:40]}"


class ExecucaoRotina(models.Model):
    etapa = models.CharField(max_length=50)
    inicio = models.DateTimeField("início")
    fim = models.DateTimeField(null=True, blank=True)
    registros_afetados = models.PositiveIntegerField(default=0)
    sucesso = models.BooleanField(default=False)
    erro = models.TextField(blank=True)

    class Meta:
        db_table = "execucao_rotina"
        ordering = ["-inicio"]
        verbose_name = "execução de rotina"
        verbose_name_plural = "execuções de rotina"

    def __str__(self):
        return f"{self.etapa} ({self.inicio:%d/%m/%Y %H:%M})"