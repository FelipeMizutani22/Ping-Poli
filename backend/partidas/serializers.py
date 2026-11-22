from rest_framework import serializers

from .models import AdversarioExterno


class AdversarioExternoSerializer(serializers.ModelSerializer):
    """Formato curto (AdversarioExt do contrato): { id, nome, clube }."""

    nome = serializers.CharField(min_length=3, max_length=100, trim_whitespace=True)
    clube = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)

    class Meta:
        model = AdversarioExterno
        fields = ["id", "nome", "clube"]


class AdversarioExternoListaSerializer(AdversarioExternoSerializer):
    """Item da busca: o AdversarioExt mais o número de partidas contra ele."""

    partidas = serializers.IntegerField(source="num_partidas", read_only=True)

    class Meta(AdversarioExternoSerializer.Meta):
        fields = ["id", "nome", "clube", "partidas"]
