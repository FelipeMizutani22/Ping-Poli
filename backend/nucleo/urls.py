from django.urls import path

from . import views

urlpatterns = [
    path("painel/", views.PainelView.as_view(), name="painel"),
]