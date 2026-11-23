from django.urls import path
from .views import CampeonatoListCreateView, CampeonatoDetailView, CampeonatoCancelarView

from .inscricoes import MinhasInscricoesView, InscricaoCreateView, InscricaoCancelarView

urlpatterns = [
    path('campeonatos/', CampeonatoListCreateView.as_view(), name='campeonatos'),
    path('campeonatos/<int:pk>/', CampeonatoDetailView.as_view(), name='campeonato-detalhe'),
    path('campeonatos/<int:pk>/cancelar/', CampeonatoCancelarView.as_view(), name='campeonato-cancelar'),

    path('inscricoes/minhas/', MinhasInscricoesView.as_view()),
    path('inscricoes/', InscricaoCreateView.as_view()),
    path('inscricoes/<int:pk>/', InscricaoCancelarView.as_view()),
]
