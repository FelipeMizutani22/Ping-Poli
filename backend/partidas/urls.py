from django.urls import path

from . import views

urlpatterns = [
    path("adversarios-externos/", views.AdversarioExternoListView.as_view(), name="adversarios-externos"),
    path("partidas/", views.PartidaListCreateView.as_view(), name="partidas"),
    path("partidas/<int:pk>/", views.PartidaDetailView.as_view(), name="partida-detalhe"),
]
