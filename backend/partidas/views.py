"""Views do app partidas: adversários externos (UC15-a), registro e listagem de partidas (UC15)."""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from contas.permissoes import Diretor
from .models import AdversarioExterno, HistoricoPartida, Partida
from .serializers import (
    AdversarioExternoListaSerializer,
    AdversarioExternoSerializer,
    ContestarSerializer,
    HistoricoPartidaSerializer,
    ModerarSerializer,
    PartidaSerializer,
    RegistrarPartidaSerializer,
)
from .servicos import (
    AdversarioJaExiste,
    ModeracaoInvalida,
    PartidaNaoPendente,
    cadastrar_adversario_externo,
    confirmar_partida,
    contestar_partida,
    moderar_partida,
    registrar_partida,
)

MSG_SO_ADVERSARIO = "Apenas o adversário indicado na partida pode confirmá-la ou contestá-la"


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


class _RespostaDoAdversarioView(APIView):
    """Base do confirmar/contestar: só o adversário responde, e só enquanto a partida está Pendente."""

    def post(self, request, pk):
        partida = get_object_or_404(Partida, pk=pk)
        if partida.adversario_id != request.user.id:
            return Response({"detail": MSG_SO_ADVERSARIO, "codigo": "nao_e_adversario"}, status=403)
        try:
            self.responder(request, partida)
        except PartidaNaoPendente as e:
            return Response({"detail": str(e), "codigo": "nao_pendente", "status": e.status}, status=409)
        return Response(PartidaSerializer(partidas_com_relacoes().get(pk=pk)).data)


class PartidaConfirmarView(_RespostaDoAdversarioView):
    """POST partidas/{id}/confirmar/ → 200 Partida (UC16)."""

    def responder(self, request, partida):
        confirmar_partida(partida.id, request.user)


class PartidaContestarView(_RespostaDoAdversarioView):
    """POST partidas/{id}/contestar/ { justificativa, sets } → 200 Partida (UC16-a)."""

    def responder(self, request, partida):
        entrada = ContestarSerializer(data=request.data, context={"partida": partida})
        entrada.is_valid(raise_exception=True)
        contestar_partida(partida.id, request.user, entrada.validated_data["justificativa"],
                          entrada.validated_data["sets"])


class PartidaModerarView(APIView):
    """POST partidas/{id}/moderar/ { decisao, motivo, dados? } → 200 Partida (UC17, só Diretor)."""

    permission_classes = [Diretor]

    def post(self, request, pk):
        partida = get_object_or_404(Partida, pk=pk)
        entrada = ModerarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        decisao = entrada.validated_data["decisao"]

        dados = None
        if decisao == "editar":
            edicao = RegistrarPartidaSerializer(
                data=entrada.validated_data.get("dados") or {},
                context={"request": request, "registrante": partida.atleta},
            )
            if not edicao.is_valid():
                return Response({"dados": edicao.errors}, status=400)
            dados = edicao.validated_data

        try:
            moderar_partida(pk, request.user, decisao, entrada.validated_data["motivo"], dados)
        except ModeracaoInvalida as e:
            return Response({"detail": str(e), "codigo": e.codigo}, status=e.status_http)
        return Response(PartidaSerializer(partidas_com_relacoes().get(pk=pk)).data)


class PartidaHistoricoView(generics.ListAPIView):
    """GET partidas/{id}/historico/ → versões anteriores, da mais recente para a mais antiga (UC17-f, só Diretor)."""

    permission_classes = [Diretor]
    serializer_class = HistoricoPartidaSerializer
    pagination_class = None

    def get_queryset(self):
        get_object_or_404(Partida, pk=self.kwargs["pk"])
        return HistoricoPartida.objects.filter(partida_id=self.kwargs["pk"]).select_related("alterado_por")
