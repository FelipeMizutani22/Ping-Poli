"""Rotas do PingPoli. Cada app declara os próprios caminhos sob /api/v1/."""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "PingPoli — Administração"
admin.site.site_title = "PingPoli"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("contas.urls")),
    path("api/v1/", include("avisos.urls")),
    path("api/v1/", include("calendario.urls")),
    path("api/v1/", include("competicoes.urls")),
    path("api/v1/", include("partidas.urls")),
    path("api/v1/", include("desempenho.urls")),
    path("api/v1/", include("nucleo.urls")),
]