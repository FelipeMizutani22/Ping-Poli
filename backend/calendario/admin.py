from django.contrib import admin

from .models import Evento, Presenca


class PresencaInline(admin.TabularInline):
    model = Presenca
    fk_name = "evento"
    extra = 0


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "tipo", "data_evento", "hora_inicio", "hora_fim", "local_evento", "status"]
    list_filter = ["tipo", "status"]
    search_fields = ["titulo", "local_evento"]
    date_hierarchy = "data_evento"
    inlines = [PresencaInline]


@admin.register(Presenca)
class PresencaAdmin(admin.ModelAdmin):
    list_display = ["evento", "atleta", "registrado_por", "data_registro"]
    list_filter = ["evento__data_evento"]