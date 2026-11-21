from django.contrib import admin

from .models import Aviso, AvisoLeitura


@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "categoria", "fixado", "autor", "data_publicacao", "data_expiracao", "excluido"]
    list_filter = ["categoria", "fixado", "excluido"]
    search_fields = ["titulo", "conteudo"]


@admin.register(AvisoLeitura)
class AvisoLeituraAdmin(admin.ModelAdmin):
    list_display = ["aviso", "atleta", "data_leitura"]