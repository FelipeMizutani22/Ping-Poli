from django.utils import timezone
from rest_framework import serializers


class FiltrosDashboardSerializer(serializers.Serializer):
    periodo = serializers.ChoiceField(choices=['3m', '6m', '12m', 'tudo', 'custom'], default='12m')
    inicio = serializers.DateField(required=False)
    fim = serializers.DateField(required=False)
    competicao = serializers.CharField(default='todas')
    tipo_adversario = serializers.ChoiceField(choices=['todos', 'poli', 'externo'], default='todos')

    def validate_competicao(self, valor):
        if valor in ('todas', 'amistoso'):
            return valor
        if not valor.isascii() or not valor.isdecimal() or int(valor) <= 0 or int(valor) > 9223372036854775807:
            raise serializers.ValidationError('Competição inválida.')
        return str(int(valor))

    def validate(self, dados):
        if dados['periodo'] == 'custom':
            erros = {campo: ['Informe a data.'] for campo in ('inicio', 'fim') if campo not in dados}
            if erros:
                raise serializers.ValidationError(erros)
            if dados['fim'] < dados['inicio']:
                raise serializers.ValidationError({'fim': ['A data final não pode ser anterior à inicial.']})
            if dados['fim'] > timezone.localdate():
                raise serializers.ValidationError({'fim': ['A data final não pode estar no futuro.']})
        return dados
