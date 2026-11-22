from django.urls import path

from . import views

urlpatterns = [
    path("avisos/", views.AvisoListCreateView.as_view(), name="avisos"),
    path("avisos/<int:pk>/", views.AvisoDetailView.as_view(), name="aviso-detalhe"),
    path("avisos/<int:pk>/fixar/", views.AvisoFixarView.as_view(), name="aviso-fixar"),
]
