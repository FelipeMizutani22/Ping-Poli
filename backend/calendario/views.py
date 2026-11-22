"""Views do app calendario: calendário unificado (UC08) e gestão de eventos pelo Diretor (UC07)."""
import calendar

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from competicoes.models import Campeonato
from contas.permissoes import AtletaAtivo, Diretor
from contas.serializers import AtletaResumoSerializer
from . import frequencia
from .models import Evento, Presenca
from .regras import dentro_da_janela, janela
from .serializers import (
    FORMATO_HORA,
    AjustePresencaSerializer,
    CancelarEventoSerializer,
    EventoEntradaSerializer,
    EventoSerializer,
    PresencaSerializer,
    RegistrarPresencaSerializer,
)
from .servicos import (
    MSG_NAO_AJUSTAVEL,
    ErroPresenca,
    EventoJaCancelado,
    cancelar_evento,
    ajustar_presencas,
    ajustavel,
    criar_evento,
    editar_evento,
    registrar_presencas,
    remover_presenca,
)

TIPOS_CALENDARIO = ("treino", "atividade", "campeonato")


def eventos_com_presenca(usuario):
    """Eventos com `presente` (o usuário marcou presença) e `total_presentes` anotados."""
    return (
        Evento.objects.select_related("criado_por")
        .annotate(
            presente=Exists(Presenca.objects.filter(evento=OuterRef("pk"), atleta=usuario)),
            total_presentes=Count("presencas", distinct=True),
        )
    )


def _periodo(params):
    """`inicio` e `fim` da query; sem eles, o mês atual (UC08 passo 2)."""
    hoje = timezone.localdate()
    inicio = parse_date(params.get("inicio") or "") or hoje.replace(day=1)
    fim = parse_date(params.get("fim") or "") or hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
    return inicio, fim


class CalendarioView(APIView):
    """
    GET calendario/?inicio=2026-11-01&fim=2026-11-30&tipo= (👤 UC08)
    Une eventos (treino, atividade) e campeonatos num formato só, ordenado por data.
    """

    def get(self, request):
        inicio, fim = _periodo(request.query_params)
        if fim < inicio:
            return Response({"fim": ["A data final deve ser igual ou posterior à inicial"]}, status=400)
        tipo = request.query_params.get("tipo") or ""
        if tipo and tipo not in TIPOS_CALENDARIO:
            return Response({"tipo": [f"Use um destes: {', '.join(TIPOS_CALENDARIO)}"]}, status=400)

        itens = []
        if tipo != "campeonato":
            eventos = eventos_com_presenca(request.user).filter(data_evento__range=(inicio, fim))
            if tipo:
                eventos = eventos.filter(tipo=tipo)
            itens += [
                {
                    "tipo": e.tipo, "id": e.id, "titulo": e.titulo, "data": e.data_evento,
                    "hora_inicio": e.hora_inicio.strftime(FORMATO_HORA),
                    "hora_fim": e.hora_fim.strftime(FORMATO_HORA),
                    "local": e.local_evento, "status": e.status, "presente": e.presente,
                    "total_presentes": e.total_presentes,
                }
                for e in eventos
            ]
        if tipo in ("", "campeonato"):
            # UC08: o campeonato ocupa os dias de data_inicio a data_fim, então entra se cruzar o período.
            campeonatos = Campeonato.objects.filter(data_inicio__lte=fim, data_fim__gte=inicio)
            itens += [
                {
                    "tipo": "campeonato", "id": c.id, "titulo": c.nome, "data": c.data_inicio,
                    "data_fim": c.data_fim, "local": c.local_campeonato, "status": c.status,
                }
                for c in campeonatos
            ]
        itens.sort(key=lambda i: (i["data"], i.get("hora_inicio", "")))
        for item in itens:
            item["data"] = item["data"].isoformat()
            if "data_fim" in item:
                item["data_fim"] = item["data_fim"].isoformat()
        return Response(itens)


class EventoCreateView(generics.CreateAPIView):
    """POST eventos/ → 201 Evento (🛡 UC07)."""

    permission_classes = [Diretor]
    serializer_class = EventoEntradaSerializer

    def create(self, request, *args, **kwargs):
        entrada = EventoEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = dict(entrada.validated_data)
        recorrencia, repetir_ate = dados.pop("recorrencia"), dados.pop("repetir_ate", None)
        dados.pop("alcance")
        evento = criar_evento(request.user, dados, repetir_ate if recorrencia == "semanal" else None)
        saida = EventoSerializer(eventos_com_presenca(request.user).get(pk=evento.pk)).data
        saida["ocorrencias"] = Evento.objects.filter(serie_id=evento.serie_id).count() if evento.serie_id else 1
        return Response(saida, status=status.HTTP_201_CREATED)


class EventoDetailView(generics.RetrieveAPIView):
    """
    GET   eventos/{id}/ → Evento (👤 UC08 passo 4).
    PATCH eventos/{id}/ → Evento (🛡 UC07-a).
    """

    serializer_class = EventoSerializer

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [Diretor()]
        return [AtletaAtivo()]

    def get_queryset(self):
        return eventos_com_presenca(self.request.user)

    def patch(self, request, *args, **kwargs):
        evento = self.get_object()
        entrada = EventoEntradaSerializer(evento, data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        dados = dict(entrada.validated_data)
        alcance = dados.pop("alcance", "esta")
        dados.pop("recorrencia", None)
        dados.pop("repetir_ate", None)
        try:
            editar_evento(evento.id, dados, alcance)
        except ValueError as e:   # mudar a data de várias ocorrências de uma vez
            return Response({"data_evento": [str(e)]}, status=400)
        return Response(EventoSerializer(self.get_queryset().get(pk=evento.id)).data)


class EventoCancelarView(APIView):
    """POST eventos/{id}/cancelar/ { motivo, alcance } → 200 Evento (🛡 UC07-b) · 409 "ja_cancelado"."""

    permission_classes = [Diretor]

    def post(self, request, pk):
        get_object_or_404(Evento, pk=pk)
        entrada = CancelarEventoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            cancelar_evento(pk, entrada.validated_data["motivo"], entrada.validated_data["alcance"])
        except EventoJaCancelado as e:
            return Response({"detail": str(e), "codigo": "ja_cancelado"}, status=status.HTTP_409_CONFLICT)
        evento = eventos_com_presenca(request.user).get(pk=pk)
        return Response(EventoSerializer(evento).data)


class PresencaListCreateView(APIView):
    """
    GET  eventos/{id}/presencas/ → { evento, janela, dentro_da_janela, presencas } (👤 UC09 passo 2)
    POST eventos/{id}/presencas/ { atletas } → 201 { registrados, ja_presentes } (👤 UC09)
         409 "fora_da_janela" / "evento_cancelado" · 400 "nao_e_treino" / "atleta_invalido"
    """

    def get(self, request, pk):
        evento = get_object_or_404(eventos_com_presenca(request.user), pk=pk)
        inicio, fim = janela(evento)
        presencas = evento.presencas.select_related("atleta", "registrado_por").order_by("data_registro")
        return Response({
            "evento": EventoSerializer(evento).data,
            "janela": {"inicio": inicio.strftime(FORMATO_HORA), "fim": fim.strftime(FORMATO_HORA)},
            "dentro_da_janela": dentro_da_janela(evento),
            "presencas": PresencaSerializer(presencas, many=True).data,
        })

    def post(self, request, pk):
        get_object_or_404(Evento, pk=pk)
        entrada = RegistrarPresencaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            registrados, ja_presentes = registrar_presencas(pk, request.user, entrada.validated_data["atletas"])
        except ErroPresenca as e:
            return Response({"detail": str(e), "codigo": e.codigo}, status=e.status_http)
        return Response({"registrados": registrados, "ja_presentes": ja_presentes}, status=status.HTTP_201_CREATED)


class PresencaDeleteView(APIView):
    """DELETE eventos/{id}/presencas/{atleta_id}/ → 204 (👤 autor dentro da janela, UC09-b · 🛡 sempre, UC10)."""

    def delete(self, request, pk, atleta_id):
        get_object_or_404(Presenca, evento_id=pk, atleta_id=atleta_id)
        try:
            remover_presenca(pk, atleta_id, request.user)
        except ErroPresenca as e:
            return Response({"detail": str(e), "codigo": e.codigo}, status=e.status_http)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _linha_ajuste(atleta, presenca):
    """Uma linha da tela de ajuste: o atleta e, se presente, quem registrou e quando."""
    return {
        "atleta": AtletaResumoSerializer(atleta).data,
        "presente": presenca is not None,
        "registrado_por": AtletaResumoSerializer(presenca.registrado_por).data if presenca else None,
        "data_registro": serializers.DateTimeField().to_representation(presenca.data_registro) if presenca else None,
    }


class AjustePresencaView(APIView):
    """
    UC10 · Ajustar presenças (🛡), sem a janela de horário e com auditoria de cada mudança.
    GET eventos/{id}/ajuste/ → { evento, ajustavel, mensagem, atletas: [{ atleta, presente, registrado_por, data_registro }] }
    PUT eventos/{id}/ajuste/ { presentes, justificativa } → 200 { incluidos, removidos }
        409 "treino_nao_ajustavel" · 400 "justificativa_obrigatoria" / "atleta_invalido"
    """

    permission_classes = [Diretor]

    def get(self, request, pk):
        evento = get_object_or_404(eventos_com_presenca(request.user), pk=pk)
        presencas = {p.atleta_id: p for p in evento.presencas.select_related("registrado_por")}
        # UC10 passo 4: todos os atletas ativos, mais quem está presente mas deixou de ser ativo
        Atleta = get_user_model()
        atletas = Atleta.objects.filter(Q(situacao="ativa") | Q(pk__in=presencas)).order_by("nome")
        pode = ajustavel(evento)
        return Response({
            "evento": EventoSerializer(evento).data,
            "ajustavel": pode,
            "mensagem": "" if pode else MSG_NAO_AJUSTAVEL,
            "atletas": [_linha_ajuste(a, presencas.get(a.id)) for a in atletas],
        })

    def put(self, request, pk):
        get_object_or_404(Evento, pk=pk)
        entrada = AjustePresencaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            incluidos, removidos = ajustar_presencas(
                pk, request.user, entrada.validated_data["presentes"], entrada.validated_data["justificativa"]
            )
        except ErroPresenca as e:
            return Response({"detail": str(e), "codigo": e.codigo}, status=e.status_http)
        return Response({"incluidos": incluidos, "removidos": removidos})


class FrequenciaView(APIView):
    """
    GET frequencia/?mes=2026-11 | ?inicio=&fim= [&atleta=] (UC11)
    O atleta vê só a própria frequência; o Diretor pode escolher qualquer atleta com `atleta=`.
    """

    def get(self, request):
        try:
            inicio, fim = frequencia.periodo(request.query_params, timezone.localdate())
        except frequencia.PeriodoInvalido as e:
            return Response({e.campo: [str(e)]}, status=400)
        atleta = request.user
        atleta_id = request.query_params.get("atleta")
        if atleta_id and str(atleta_id) != str(request.user.id):
            if not request.user.eh_diretor:   # UC11-f
                self.permission_denied(request, message=Diretor.message)
            atleta = get_object_or_404(get_user_model(), pk=atleta_id)
        return Response(frequencia.relatorio_individual(atleta, inicio, fim))


class FrequenciaEquipeView(APIView):
    """GET frequencia/equipe/?mes= | ?inicio=&fim= (🛡 UC11-a): matriz atletas ativos × treinos realizados."""

    permission_classes = [Diretor]

    def get(self, request):
        try:
            inicio, fim = frequencia.periodo(request.query_params, timezone.localdate())
        except frequencia.PeriodoInvalido as e:
            return Response({e.campo: [str(e)]}, status=400)
        return Response(frequencia.relatorio_equipe(inicio, fim))
