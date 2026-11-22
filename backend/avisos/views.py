"""Views do app avisos: quadro de avisos (UC06) e gestão pelo Diretor (UC05)."""
from django.db.models import Exists, OuterRef, Q
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from contas.permissoes import AtletaAtivo, Diretor
from .models import Aviso, AvisoLeitura
from .serializers import AvisoEntradaSerializer, AvisoSerializer
from .servicos import (
    LimiteFixadosAtingido,
    alternar_fixado,
    editar_aviso,
    excluir_aviso,
    publicar_aviso,
    registrar_leitura,
)

MSG_INDISPONIVEL = "Este aviso não está mais disponível"


def avisos_visiveis(usuario):
    """
    Avisos que o usuário pode ver, com `lido` anotado.
    Ninguém vê os excluídos; o Atleta não vê os expirados (data_expiracao < hoje). O Diretor vê.
    """
    qs = (
        Aviso.objects.filter(excluido=False)
        .select_related("autor")
        .annotate(lido=Exists(AvisoLeitura.objects.filter(aviso=OuterRef("pk"), atleta=usuario)))
        .order_by("-fixado", "-data_publicacao")
    )
    if not usuario.eh_diretor:
        qs = qs.filter(Q(data_expiracao__isnull=True) | Q(data_expiracao__gte=timezone.localdate()))
    return qs


def resposta_limite(e):
    return Response({"detail": str(e), "codigo": "limite_fixados"}, status=status.HTTP_409_CONFLICT)


class AvisoContextoMixin:
    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto["diretor"] = self.request.user.eh_diretor
        return contexto

    def saida(self, aviso_id):
        aviso = avisos_visiveis(self.request.user).get(pk=aviso_id)
        return AvisoSerializer(aviso, context=self.get_serializer_context()).data


class AvisoListCreateView(AvisoContextoMixin, generics.ListCreateAPIView):
    """
    GET  avisos/?categoria= → [Aviso] (👤 UC06). Fixados primeiro, depois os mais recentes.
    POST avisos/ → 201 Aviso (🛡 UC05) · 409 "limite_fixados".
    """

    serializer_class = AvisoSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [Diretor()]
        return [AtletaAtivo()]

    def get_queryset(self):
        qs = avisos_visiveis(self.request.user)
        categoria = self.request.query_params.get("categoria")
        if categoria:
            qs = qs.filter(categoria=categoria)
        return qs

    def create(self, request, *args, **kwargs):
        entrada = AvisoEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            aviso = publicar_aviso(request.user, dict(entrada.validated_data))
        except LimiteFixadosAtingido as e:
            return resposta_limite(e)
        return Response(self.saida(aviso.id), status=status.HTTP_201_CREATED)


class AvisoDetailView(AvisoContextoMixin, generics.RetrieveAPIView):
    """
    GET    avisos/{id}/ → Aviso e registra a leitura (👤 UC06, n×n).
    PATCH  avisos/{id}/ → Aviso (🛡 UC05-a) · 409 "limite_fixados".
    DELETE avisos/{id}/ → 204, exclusão lógica (🛡 UC05-b).
    """

    serializer_class = AvisoSerializer

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [Diretor()]
        return [AtletaAtivo()]

    def get_queryset(self):
        return avisos_visiveis(self.request.user)

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise Http404(MSG_INDISPONIVEL)

    def retrieve(self, request, *args, **kwargs):
        aviso = self.get_object()
        registrar_leitura(aviso, request.user)
        return Response(self.saida(aviso.id))

    def patch(self, request, *args, **kwargs):
        aviso = self.get_object()
        entrada = AvisoEntradaSerializer(aviso, data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        try:
            editar_aviso(aviso.id, dict(entrada.validated_data))
        except LimiteFixadosAtingido as e:
            return resposta_limite(e)
        return Response(self.saida(aviso.id))

    def delete(self, request, *args, **kwargs):
        excluir_aviso(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvisoFixarView(AvisoContextoMixin, APIView):
    """POST avisos/{id}/fixar/ → 200 Aviso, alterna fixado (🛡 UC05-c) · 409 "limite_fixados"."""

    permission_classes = [Diretor]

    def get_serializer_context(self):
        return {"request": self.request, "diretor": True}

    def post(self, request, pk):
        if not Aviso.objects.filter(pk=pk, excluido=False).exists():
            raise Http404(MSG_INDISPONIVEL)
        try:
            alternar_fixado(pk)
        except LimiteFixadosAtingido as e:
            return resposta_limite(e)
        return Response(self.saida(pk))
