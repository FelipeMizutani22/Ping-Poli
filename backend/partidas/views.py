"""Views do app partidas: adversários externos (UC15-a), registro e listagem de partidas (UC15)."""
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.response import Response

from contas.permissoes import Diretor
from .models import AdversarioExterno, Partida
from .serializers import (
    AdversarioExternoListaSerializer,
    AdversarioExternoSerializer,
    PartidaSerializer,
    RegistrarPartidaSerializer,
)
from .servicos import AdversarioJaExiste, cadastrar_adversario_externo, registrar_partida


class AdversarioExternoListView(generics.ListCreateAPIView):
    """
    GET  adversarios-externos/?q=carlos → [{ id, nome, clube, partidas }]
    POST adversarios-externos/ { nome, clube } → 201 AdversarioExt · 409 "ja_existe" se o nome já existe.
    """

    pagination_class = None

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdversarioExternoListaSerializer
        return AdversarioExternoSerializer

    def get_queryset(self):
        qs = AdversarioExterno.objects.annotate(num_partidas=Count("partidas"))
        termo = (self.request.query_params.get("q") or "").strip()
        if termo:
            qs = qs.filter(nome__icontains=termo)
        return qs.order_by("nome")

    def create(self, request, *args, **kwargs):
        serializer = AdversarioExternoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            adversario = cadastrar_adversario_externo(**serializer.validated_data)
        except AdversarioJaExiste as e:
            return Response(
                {
                    "detail": str(e),
                    "codigo": "ja_existe",
                    "existente": AdversarioExternoSerializer(e.existente).data,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(AdversarioExternoSerializer(adversario).data, status=status.HTTP_201_CREATED)


def partidas_com_relacoes():
    """Partidas com tudo o que o PartidaSerializer usa, carregado em poucas consultas."""
    return Partida.objects.select_related(
        "atleta", "adversario", "adversario_externo", "campeonato", "categoria"
    ).prefetch_related("sets", "contestacoes__contestante", "contestacoes__resolvida_por")


class PartidaListCreateView(generics.ListCreateAPIView):
    """
    GET  partidas/?escopo=minhas|pendentes|contestadas|todas (contestadas e todas: só Diretor)
    POST partidas/ → 201 Partida (UC15)
    """

    serializer_class = PartidaSerializer
    pagination_class = None
    ESCOPOS = ("minhas", "pendentes", "contestadas", "todas")
    ESCOPOS_DIRETOR = ("contestadas", "todas")

    def list(self, request, *args, **kwargs):
        escopo = request.query_params.get("escopo") or "minhas"
        if escopo not in self.ESCOPOS:
            return Response({"escopo": [f"Use um destes: {', '.join(self.ESCOPOS)}"]}, status=400)
        if escopo in self.ESCOPOS_DIRETOR and not request.user.eh_diretor:
            self.permission_denied(request, message=Diretor.message)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        usuario = self.request.user
        params = self.request.query_params
        escopo = params.get("escopo") or "minhas"
        qs = partidas_com_relacoes()

        if escopo == "pendentes":  # lista do UC16: aguardando a MINHA resposta
            return qs.filter(status=Partida.Status.PENDENTE, adversario=usuario)
        if escopo == "contestadas":
            return qs.filter(status=Partida.Status.CONTESTADA)
        if escopo == "todas":
            return self._filtrar(qs, params)
        # minhas: eu registrei OU fui o adversário, menos as removidas
        return qs.filter(Q(atleta=usuario) | Q(adversario=usuario)).exclude(status=Partida.Status.REMOVIDA)

    def _filtrar(self, qs, params):
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if (params.get("atleta") or "").isdigit():
            qs = qs.filter(Q(atleta_id=params["atleta"]) | Q(adversario_id=params["atleta"]))
        if (params.get("campeonato") or "").isdigit():
            qs = qs.filter(campeonato_id=params["campeonato"])
        if params.get("tipo_adversario"):
            qs = qs.filter(tipo_adversario=params["tipo_adversario"])
        if parse_date(params.get("inicio") or ""):
            qs = qs.filter(data_jogo__gte=parse_date(params["inicio"]))
        if parse_date(params.get("fim") or ""):
            qs = qs.filter(data_jogo__lte=parse_date(params["fim"]))
        return qs

    def create(self, request, *args, **kwargs):
        entrada = RegistrarPartidaSerializer(data=request.data, context={"request": request})
        entrada.is_valid(raise_exception=True)
        partida = registrar_partida(request.user, entrada.validated_data)
        partida = partidas_com_relacoes().get(pk=partida.pk)
        return Response(PartidaSerializer(partida).data, status=status.HTTP_201_CREATED)


class PartidaDetailView(generics.RetrieveAPIView):
    """GET partidas/{id}/ → Partida. Só os dois jogadores ou um Diretor (os outros recebem 404)."""

    serializer_class = PartidaSerializer

    def get_queryset(self):
        qs = partidas_com_relacoes()
        usuario = self.request.user
        if usuario.eh_diretor:
            return qs
        return qs.filter(Q(atleta=usuario) | Q(adversario=usuario))
