"""Serializers do app avisos (UC05, UC06 · 03_CONTRATO_API §2)."""
from django.utils import timezone
from rest_framework import serializers

from contas.serializers import AtletaResumoSerializer
from .models import Aviso

TAMANHO_TRECHO = 200
MSG_EXPIRACAO_PASSADA = "A data de expiração deve ser hoje ou uma data futura"


class AvisoSerializer(serializers.ModelSerializer):
    """Saída: o objeto Aviso do contrato. `lido` vem da anotação feita na view."""

    autor = AtletaResumoSerializer(read_only=True)
    trecho = serializers.SerializerMethodField()
    lido = serializers.SerializerMethodField()

    class Meta:
        model = Aviso
        fields = [
            "id", "titulo", "conteudo", "trecho", "categoria", "fixado", "autor",
            "data_publicacao", "data_edicao", "data_expiracao", "lido",
        ]

    def get_trecho(self, aviso):
        return aviso.conteudo[:TAMANHO_TRECHO]

    def get_lido(self, aviso):
        return bool(getattr(aviso, "lido", False))

    def to_representation(self, aviso):
        dados = super().to_representation(aviso)
        # O Diretor também recebe os expirados, marcados com "expirado": true (contrato §2).
        if self.context.get("diretor"):
            dados["expirado"] = aviso.data_expiracao is not None and aviso.data_expiracao < timezone.localdate()
        return dados


class AvisoEntradaSerializer(serializers.ModelSerializer):
    """Entrada do POST e do PATCH (UC05). Só valida: quem grava é servicos.py."""

    titulo = serializers.CharField(min_length=3, max_length=100, trim_whitespace=True)
    conteudo = serializers.CharField(min_length=10, max_length=5000, trim_whitespace=True)
    notificar_email = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = Aviso
        fields = ["titulo", "conteudo", "categoria", "fixado", "data_expiracao", "notificar_email"]
        extra_kwargs = {"categoria": {"required": True}}

    def validate_data_expiracao(self, valor):
        if valor is not None and valor < timezone.localdate():
            raise serializers.ValidationError(MSG_EXPIRACAO_PASSADA)
        return valor
