"""Serializers do app calendario (UC07, UC08 · 03_CONTRATO_API §3)."""
import calendar
from datetime import date

from django.utils import timezone
from rest_framework import serializers

from contas.serializers import AtletaResumoSerializer
from .models import Evento

FORMATO_HORA = "%H:%M"
MSG_DATA_PASSADA = "A data do evento deve ser hoje ou uma data futura"
MSG_HORARIO = "O horário de término deve ser posterior ao de início"
MSG_REPETIR_OBRIGATORIO = "Informe até quando o evento se repete"
MSG_REPETIR_ANTES = "A data final da recorrência deve ser posterior à data do evento"
MSG_REPETIR_LONGE = "A recorrência pode ir no máximo até 6 meses depois da data do evento"
MESES_MAX_RECORRENCIA = 6


def _somar_meses(dia, meses):
    mes = dia.month - 1 + meses
    ano, mes = dia.year + mes // 12, mes % 12 + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


class EventoSerializer(serializers.ModelSerializer):
    """Saída: o Evento completo. `presente` e `total_presentes` vêm das anotações da view."""

    hora_inicio = serializers.TimeField(format=FORMATO_HORA)
    hora_fim = serializers.TimeField(format=FORMATO_HORA)
    criado_por = AtletaResumoSerializer(read_only=True)
    presente = serializers.SerializerMethodField()
    total_presentes = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = [
            "id", "tipo", "titulo", "data_evento", "hora_inicio", "hora_fim", "local_evento", "descricao",
            "status", "motivo_cancelamento", "serie_id", "criado_por", "presente", "total_presentes",
        ]

    def get_presente(self, evento):
        return bool(getattr(evento, "presente", False))

    def get_total_presentes(self, evento):
        return getattr(evento, "total_presentes", 0)


class EventoEntradaSerializer(serializers.ModelSerializer):
    """Entrada do POST e do PATCH (UC07). Só valida: quem grava é servicos.py."""

    titulo = serializers.CharField(min_length=3, max_length=100, trim_whitespace=True)
    local_evento = serializers.CharField(max_length=100, trim_whitespace=True)
    descricao = serializers.CharField(max_length=1000, required=False, allow_blank=True, trim_whitespace=True)
    hora_inicio = serializers.TimeField(input_formats=[FORMATO_HORA, "%H:%M:%S"])
    hora_fim = serializers.TimeField(input_formats=[FORMATO_HORA, "%H:%M:%S"])
    # C11 · recorrência (só na criação) e alcance da edição em uma série (UC07-a.2)
    recorrencia = serializers.ChoiceField(choices=["nenhuma", "semanal"], default="nenhuma", write_only=True)
    repetir_ate = serializers.DateField(required=False, allow_null=True, write_only=True)
    alcance = serializers.ChoiceField(choices=["esta", "seguintes"], default="esta", write_only=True)

    class Meta:
        model = Evento
        fields = ["tipo", "titulo", "data_evento", "hora_inicio", "hora_fim", "local_evento", "descricao",
                  "recorrencia", "repetir_ate", "alcance"]

    def validate_data_evento(self, valor):
        # Na edição, só a data nova precisa ser futura: um evento passado pode ter outros campos corrigidos.
        mudou = self.instance is None or valor != self.instance.data_evento
        if mudou and valor < timezone.localdate():
            raise serializers.ValidationError(MSG_DATA_PASSADA)
        return valor

    def validate(self, dados):
        inicio = dados.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        fim = dados.get("hora_fim", getattr(self.instance, "hora_fim", None))
        if inicio and fim and fim <= inicio:
            raise serializers.ValidationError({"hora_fim": [MSG_HORARIO]})
        if self.instance is None and dados.get("recorrencia") == "semanal":
            ate, dia = dados.get("repetir_ate"), dados["data_evento"]
            if not ate:
                raise serializers.ValidationError({"repetir_ate": [MSG_REPETIR_OBRIGATORIO]})
            if ate <= dia:
                raise serializers.ValidationError({"repetir_ate": [MSG_REPETIR_ANTES]})
            if ate > _somar_meses(dia, MESES_MAX_RECORRENCIA):
                raise serializers.ValidationError({"repetir_ate": [MSG_REPETIR_LONGE]})
        return dados


class CancelarEventoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True, default="", trim_whitespace=True)
    alcance = serializers.ChoiceField(choices=["esta", "seguintes"], default="esta")


class PresencaSerializer(serializers.Serializer):
    """Item da lista de presentes (UC09 passo 2): quem, quem registrou e quando."""

    atleta = AtletaResumoSerializer()
    registrado_por = AtletaResumoSerializer()
    data_registro = serializers.DateTimeField()


class RegistrarPresencaSerializer(serializers.Serializer):
    """{ "atletas": [5, 8] } · lista vazia ou ausente = o próprio usuário."""

    atletas = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)


class AjustePresencaSerializer(serializers.Serializer):
    """UC10: { "presentes": [ids], "justificativa": "…" }. A justificativa é obrigatória se houver remoção."""

    presentes = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=True)
    justificativa = serializers.CharField(min_length=5, max_length=200, required=False, allow_blank=True,
                                          default="", trim_whitespace=True)
