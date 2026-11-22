from django.urls import path

from . import views

urlpatterns = [
    path("adversarios-externos/", views.AdversarioExternoListView.as_view(), name="adversarios-externos"),
    path("partidas/", views.PartidaListCreateView.as_view(), name="partidas"),
    path("partidas/<int:pk>/", views.PartidaDetailView.as_view(), name="partida-detalhe"),
    path("partidas/<int:pk>/confirmar/", views.PartidaConfirmarView.as_view(), name="partida-confirmar"),
    path("partidas/<int:pk>/contestar/", views.PartidaContestarView.as_view(), name="partida-contestar"),
    path("partidas/<int:pk>/moderar/", views.PartidaModerarView.as_view(), name="partida-moderar"),
    path("partidas/<int:pk>/historico/", views.PartidaHistoricoView.as_view(), name="partida-historico"),
]
