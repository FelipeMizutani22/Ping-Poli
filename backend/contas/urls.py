from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("cursos/", views.CursoListView.as_view(), name="cursos"),
    path("atletas/opcoes/", views.AtletaOpcoesView.as_view(), name="atletas-opcoes")
]