from django.contrib import admin

from .models import Atleta, Curso


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    search_fields = ["nome"]


@admin.register(Atleta)
class AtletaAdmin(admin.ModelAdmin):
    list_display = ["nome", "nusp", "email", "curso", "papel", "situacao", "last_login"]
    list_filter = ["papel", "situacao", "curso"]
    search_fields = ["nome", "email", "nusp"]
    readonly_fields = ["password", "last_login", "data_solicitacao"]
    exclude = ["groups", "user_permissions"]