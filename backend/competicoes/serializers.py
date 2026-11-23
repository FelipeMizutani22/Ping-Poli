"""Contrato de entrada e saída dos campeonatos (UC12/UC13)."""
from django.utils import timezone
from rest_framework import serializers
from .models import Campeonato, Categoria


class CategoriaSerializer(serializers.ModelSerializer):
    vagas_restantes = serializers.SerializerMethodField()
    inscrito = serializers.BooleanField(read_only=True)

    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'vagas', 'vagas_restantes', 'inscrito']

    def get_vagas_restantes(self, categoria):
        return None if categoria.vagas is None else categoria.vagas - categoria.total_inscritos


class CampeonatoSerializer(serializers.ModelSerializer):
    categorias = CategoriaSerializer(many=True, read_only=True)
    inscrito = serializers.SerializerMethodField()

    class Meta:
        model = Campeonato
        fields = ['id', 'nome', 'organizador', 'local_campeonato', 'data_inicio', 'data_fim',
                  'abertura_inscricoes', 'encerramento_inscricoes', 'valor_inscricao',
                  'link_regulamento', 'observacoes', 'status', 'categorias', 'inscrito']

    def get_inscrito(self, campeonato):
        return any(c.inscrito for c in campeonato.categorias.all())


class CategoriaEntradaSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1, required=False)
    nome = serializers.CharField(min_length=2, max_length=50)
    vagas = serializers.IntegerField(min_value=1, max_value=32767, allow_null=True, required=False, default=None)


class CampeonatoEntradaSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(min_length=3, max_length=120)
    categorias = CategoriaEntradaSerializer(many=True, allow_empty=False, required=True)
    anunciar = serializers.BooleanField(default=True, write_only=True)
    confirmar_duplicada = serializers.BooleanField(default=False, write_only=True)

    class Meta:
        model = Campeonato
        fields = ['nome', 'organizador', 'local_campeonato', 'data_inicio', 'data_fim',
                  'abertura_inscricoes', 'encerramento_inscricoes', 'valor_inscricao',
                  'link_regulamento', 'observacoes', 'categorias', 'status', 'anunciar', 'confirmar_duplicada']
        extra_kwargs = {'valor_inscricao': {'min_value': 0}, 'status': {'required': False}}

    def validate_categorias(self, itens):
        completas = CategoriaEntradaSerializer(data=itens, many=True)
        completas.is_valid(raise_exception=True)
        itens = completas.validated_data
        nomes = [item['nome'].casefold() for item in itens]
        ids = [item['id'] for item in itens if 'id' in item]
        if len(nomes) != len(set(nomes)) or len(ids) != len(set(ids)):
            raise serializers.ValidationError('As categorias não podem repetir nome ou id.')
        if self.instance is None and ids:
            raise serializers.ValidationError('Não informe ids ao criar categorias.')
        return itens

    def validate(self, dados):
        def valor(campo):
            return dados.get(campo, getattr(self.instance, campo, None))
        inicio, fim = valor('data_inicio'), valor('data_fim')
        abertura, encerramento = valor('abertura_inscricoes'), valor('encerramento_inscricoes')
        erros = {}
        if inicio and fim and fim < inicio:
            erros['data_fim'] = ['O término deve ser igual ou posterior ao início.']
        if abertura and encerramento and abertura >= encerramento:
            erros['encerramento_inscricoes'] = ['A abertura deve ser anterior ao encerramento.']
        # O campeonato tem data, sem horário: o prazo pode cair no próprio dia de início.
        if inicio and encerramento and timezone.localtime(encerramento).date() > inicio:
            erros['encerramento_inscricoes'] = ['O encerramento deve ocorrer até a data de início do campeonato.']
        if self.instance is None and dados.get('status', 'planejado') != 'planejado':
            erros['status'] = ['O status inicial é definido pelas datas.']
        if erros:
            raise serializers.ValidationError(erros)
        return dados


class CancelamentoSerializer(serializers.Serializer):
    motivo = serializers.CharField(min_length=10, max_length=300)
