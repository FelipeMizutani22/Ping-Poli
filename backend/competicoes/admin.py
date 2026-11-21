from django.contrib import admin

from .models import Campeonato, Categoria, Inscricao


class CategoriaInline(admin.TabularInline):
    model = Categoria
    extra = 1


@admin.register(Campeonato)
class CampeonatoAdmin(admin.ModelAdmin):
    list_display = ["nome", "status", "data_inicio", "data_fim", "abertura_inscricoes", "encerramento_inscricoes"]
    list_filter = ["status"]
    search_fields = ["nome", "organizador"]
    inlines = [CategoriaInline]


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ["atleta", "categoria", "status", "colocacao", "destaque", "data_inscricao"]
    list_filter = ["status", "categoria__campeonato"]
    search_fields = ["atleta__nome"]