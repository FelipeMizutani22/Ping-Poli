from django.urls import path

from . import views

urlpatterns = [
    path("painel/", views.PainelView.as_view(), name="painel"),
    path("notificacoes/", views.NotificacaoListView.as_view(), name="notificacoes"),
    path("notificacoes/marcar-todas/", views.MarcarTodasView.as_view(), name="notificacoes-marcar-todas"),
    path("notificacoes/<int:pk>/lida/", views.MarcarLidaView.as_view(), name="notificacao-lida"),
]