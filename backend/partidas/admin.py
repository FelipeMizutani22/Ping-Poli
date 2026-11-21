from django.contrib import admin

from .models import AdversarioExterno, Contestacao, HistoricoPartida, Partida, SetPartida


class SetOficialInline(admin.TabularInline):
    model = SetPartida
    extra = 0
    fields = ["numero", "pontos_atleta", "pontos_adversario", "contestacao"]


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ["id", "data_jogo", "atleta", "tipo_adversario", "adversario", "adversario_externo",
                    "campeonato", "formato", "status"]
    list_filter = ["status", "tipo_adversario", "campeonato"]
    search_fields = ["atleta__nome", "adversario__nome", "adversario_externo__nome"]
    date_hierarchy = "data_jogo"
    inlines = [SetOficialInline]


@admin.register(AdversarioExterno)
class AdversarioExternoAdmin(admin.ModelAdmin):
    list_display = ["nome", "clube"]
    search_fields = ["nome", "clube"]


@admin.register(Contestacao)
class ContestacaoAdmin(admin.ModelAdmin):
    list_display = ["partida", "contestante", "data_contestacao", "resolvida_por", "data_resolucao"]


@admin.register(HistoricoPartida)
class HistoricoPartidaAdmin(admin.ModelAdmin):
    list_display = ["partida", "alterado_por", "motivo", "data_alteracao"]