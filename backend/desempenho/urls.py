from django.urls import path
from .views import DashboardView

urlpatterns = [
    path('desempenho/', DashboardView.as_view(), name='dashboard-desempenho'),
]
