from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("cursos/", views.CursoListView.as_view(), name="cursos"),
    path("cadastro/", views.CadastroView.as_view(), name="cadastro"),
    path("atletas/opcoes/", views.AtletaOpcoesView.as_view(), name="atletas-opcoes"),
    path("atletas/", views.AtletaListView.as_view(), name="atletas"),
    path("atletas/<int:pk>/", views.AtletaDetailView.as_view(), name="atleta-detalhe"),
    path("atletas/<int:pk>/aprovar/", views.AprovarView.as_view(), name="atleta-aprovar"),
    path("atletas/<int:pk>/recusar/", views.RecusarView.as_view(), name="atleta-recusar"),
]