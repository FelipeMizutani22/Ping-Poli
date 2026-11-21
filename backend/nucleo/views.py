"""Views do app nucleo: painel da página inicial e notificações (sino)."""
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notificacao
from .painel import montar_painel
from .serializers import NotificacaoSerializer


class PainelView(APIView):
    """GET painel/ → tudo o que a página inicial precisa, numa chamada só (T03/T04)."""

    def get(self, request):
        return Response(montar_painel(request.user))


class NotificacaoListView(generics.ListAPIView):
    """GET notificacoes/?nao_lidas=1 → as 50 notificações mais recentes do próprio usuário."""

    serializer_class = NotificacaoSerializer
    pagination_class = None
    LIMITE = 50

    def get_queryset(self):
        qs = Notificacao.objects.filter(destinatario=self.request.user)
        if self.request.query_params.get("nao_lidas") == "1":
            qs = qs.filter(lida=False)
        return qs.order_by("-data_criacao", "-id")[: self.LIMITE]


class MarcarLidaView(APIView):
    """POST notificacoes/{id}/lida/ → marca uma notificação do próprio usuário como lida."""

    def post(self, request, pk):
        notificacao = get_object_or_404(Notificacao, pk=pk, destinatario=request.user)
        if not notificacao.lida:
            notificacao.lida = True
            notificacao.save(update_fields=["lida"])
        return Response(NotificacaoSerializer(notificacao).data)


class MarcarTodasView(APIView):
    """POST notificacoes/marcar-todas/ → marca todas as não lidas do próprio usuário."""

    def post(self, request):
        marcadas = Notificacao.objects.filter(destinatario=request.user, lida=False).update(lida=True)
        return Response({"marcadas": marcadas})