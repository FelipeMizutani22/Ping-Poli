from django.urls import path
from .views import DashboardView, EquipeView

urlpatterns = [
    path('desempenho/equipe/', EquipeView.as_view(), name='desempenho-equipe'),
    path('desempenho/', DashboardView.as_view(), name='dashboard-desempenho'),
]
