from django.urls import path
from .views import CampeonatoListCreateView, CampeonatoDetailView, CampeonatoCancelarView

urlpatterns = [
    path('campeonatos/', CampeonatoListCreateView.as_view(), name='campeonatos'),
    path('campeonatos/<int:pk>/', CampeonatoDetailView.as_view(), name='campeonato-detalhe'),
    path('campeonatos/<int:pk>/cancelar/', CampeonatoCancelarView.as_view(), name='campeonato-cancelar'),
]
