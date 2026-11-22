from django.urls import path

from . import views

urlpatterns = [
    path("adversarios-externos/", views.AdversarioExternoListView.as_view(), name="adversarios-externos"),
]
