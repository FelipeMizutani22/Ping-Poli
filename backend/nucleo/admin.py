from django.contrib import admin

from .models import Auditoria, ExecucaoRotina, Notificacao


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ["data_acao", "entidade", "registro_id", "acao", "autor"]
    list_filter = ["entidade", "acao"]


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ["destinatario", "tipo", "mensagem", "lida", "data_criacao"]
    list_filter = ["tipo", "lida"]


@admin.register(ExecucaoRotina)
class ExecucaoRotinaAdmin(admin.ModelAdmin):
    list_display = ["etapa", "inicio", "fim", "registros_afetados", "sucesso"]
    list_filter = ["etapa", "sucesso"]