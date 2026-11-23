from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.response import Response

from contas.permissoes import AtletaAtivo
from contas.serializers import AtletaResumoSerializer
from . import calculos, consultas
from .serializers import FiltrosDashboardSerializer


class DashboardView(generics.GenericAPIView):
    permission_classes = [AtletaAtivo]
    serializer_class = FiltrosDashboardSerializer

    def get(self, request):
        atleta = request.user
        # O parâmetro é ignorado por completo para atletas comuns (UC18-f).
        if atleta.papel == 'diretor' and 'atleta' in request.query_params:
            campo = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
            try:
                atleta_id = campo.run_validation(request.query_params['atleta'])
            except serializers.ValidationError as erro:
                raise serializers.ValidationError({'atleta': erro.detail})
            atleta = get_object_or_404(get_user_model(), pk=atleta_id)

        filtros = self.get_serializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        dados = filtros.validated_data
        hoje = timezone.localdate()
        primeira = consultas.primeira_data_do_atleta(atleta, hoje) if dados['periodo'] == 'tudo' else None
        inicio, fim = calculos.resolver_periodo(
            dados['periodo'], hoje=hoje, inicio=dados.get('inicio'),
            fim=dados.get('fim'), primeira_data=primeira,
        )
        linhas = consultas.linhas_do_atleta(
            atleta, inicio, fim, dados['competicao'], dados['tipo_adversario']
        )
        return Response({
            'atleta': AtletaResumoSerializer(atleta).data,
            'filtros': {
                'periodo': dados['periodo'], 'inicio': inicio, 'fim': fim,
                'competicao': dados['competicao'], 'tipo_adversario': dados['tipo_adversario'],
            },
            'indicadores': calculos.indicadores(linhas),
            'evolucao_mensal': calculos.evolucao_mensal(linhas, inicio, fim),
            'por_competicao': calculos.por_competicao(linhas),
            'colocacoes': consultas.colocacoes_do_atleta(atleta, inicio, fim, dados['competicao']),
            'recentes': calculos.recentes(linhas),
            'mais_enfrentados': calculos.mais_enfrentados(linhas),
        })
