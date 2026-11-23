from django.urls import path
from .views import CampeonatoListCreateView, CampeonatoDetailView, CampeonatoCancelarView

from .inscricoes import MinhasInscricoesView, InscricaoCreateView, InscricaoCancelarView

from .gestao import GestaoInscricoesView, ResultadosView, ResultadoView, RemoverInscricaoView

urlpatterns = [
    path('campeonatos/<int:pk>/inscricoes/', GestaoInscricoesView.as_view()),
    path('campeonatos/<int:pk>/resultados/', ResultadosView.as_view()),
    path('inscricoes/<int:pk>/resultado/', ResultadoView.as_view()),
    path('inscricoes/<int:pk>/remover/', RemoverInscricaoView.as_view()),
    path('campeonatos/', CampeonatoListCreateView.as_view(), name='campeonatos'),
    path('campeonatos/<int:pk>/', CampeonatoDetailView.as_view(), name='campeonato-detalhe'),
    path('campeonatos/<int:pk>/cancelar/', CampeonatoCancelarView.as_view(), name='campeonato-cancelar'),

    path('inscricoes/minhas/', MinhasInscricoesView.as_view()),
    path('inscricoes/', InscricaoCreateView.as_view()),
    path('inscricoes/<int:pk>/', InscricaoCancelarView.as_view()),
]
