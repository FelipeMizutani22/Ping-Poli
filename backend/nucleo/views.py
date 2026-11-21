"""Views do app nucleo."""
from rest_framework.response import Response
from rest_framework.views import APIView

from .painel import montar_painel


class PainelView(APIView):
    """GET painel/ → tudo o que a página inicial precisa, numa chamada só (T03/T04)."""

    def get(self, request):
        return Response(montar_painel(request.user))