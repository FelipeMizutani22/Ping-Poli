from django.urls import path
from .views import DashboardView, EquipeView, ConfrontoView

urlpatterns = [
    path('desempenho/confronto/', ConfrontoView.as_view(), name='desempenho-confronto'),
    path('desempenho/equipe/', EquipeView.as_view(), name='desempenho-equipe'),
    path('desempenho/', DashboardView.as_view(), name='dashboard-desempenho'),
]
