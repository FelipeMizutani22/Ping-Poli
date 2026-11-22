from django.urls import path

from . import views

urlpatterns = [
    path("calendario/", views.CalendarioView.as_view(), name="calendario"),
    path("eventos/", views.EventoCreateView.as_view(), name="eventos"),
    path("eventos/<int:pk>/", views.EventoDetailView.as_view(), name="evento-detalhe"),
    path("eventos/<int:pk>/cancelar/", views.EventoCancelarView.as_view(), name="evento-cancelar"),
    path("eventos/<int:pk>/presencas/", views.PresencaListCreateView.as_view(), name="evento-presencas"),
    path("eventos/<int:pk>/presencas/<int:atleta_id>/", views.PresencaDeleteView.as_view(), name="evento-presenca"),
]
