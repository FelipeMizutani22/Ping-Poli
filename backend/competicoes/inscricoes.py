"""Inscrições próprias com reserva atômica de vagas."""
from django.db import connection, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from contas.permissoes import AtletaAtivo
from nucleo.servicos import enviar_email
from .models import Campeonato, Categoria, Inscricao
from .servicos import _sincronizar


class ConflitoInscricao(APIException):
    status_code = 409

    def __init__(self, codigo, detail, **extra):
        self.detail = {'codigo': codigo, 'detail': detail, **extra}


class EntradaInscricao(serializers.Serializer):
    categorias = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    observacoes = serializers.CharField(max_length=300, allow_blank=True, required=False, default='')
    ciencia_regulamento = serializers.BooleanField()

    def validate_categorias(self, valor):
        if len(valor) != len(set(valor)):
            raise serializers.ValidationError('Selecione cada categoria apenas uma vez.')
        return valor

    def validate_ciencia_regulamento(self, valor):
        if not valor:
            raise serializers.ValidationError('Confirme a ciência do regulamento.')
        return valor


class SaidaInscricao(serializers.ModelSerializer):
    categoria = serializers.SerializerMethodField()
    campeonato = serializers.SerializerMethodField()

    class Meta:
        model = Inscricao
        fields = ['id', 'categoria', 'campeonato', 'status', 'data_inscricao', 'colocacao', 'destaque']

    def get_categoria(self, obj):
        return {'id': obj.categoria_id, 'nome': obj.categoria.nome}

    def get_campeonato(self, obj):
        c = obj.categoria.campeonato
        return {'id': c.pk, 'nome': c.nome}


def preparar_transacao():
    # SQLite não implementa SELECT FOR UPDATE. Adquirir o bloqueio de escrita
    # antes de qualquer leitura evita duas transações aprovarem a última vaga.
    if connection.vendor == 'sqlite':
        Campeonato.objects.filter(pk__in=Campeonato.objects.values('pk')[:1]).update(status=F('status'))


def conferir_prazo(c):
    agora = timezone.now()
    if c.status not in ('planejado', 'inscricoes_abertas') or not c.abertura_inscricoes <= agora < c.encerramento_inscricoes:
        raise ConflitoInscricao('inscricoes_fechadas', 'As inscrições para este campeonato não estão abertas. Em caso de dúvida, procure a Diretoria')
    if c.status == 'planejado':
        _sincronizar(c, agora)


@transaction.atomic
def inscrever(atleta, dados):
    preparar_transacao()
    ids = dados['categorias']
    encontrados = list(Categoria.objects.filter(pk__in=ids).values_list('campeonato_id', flat=True))
    if len(encontrados) != len(ids) or len(set(encontrados)) != 1:
        raise serializers.ValidationError({'categorias': ['Selecione categorias válidas de um único campeonato.']})
    campeonato = Campeonato.objects.select_for_update().get(pk=encontrados[0])
    conferir_prazo(campeonato)
    categorias = list(Categoria.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
    if len(categorias) != len(ids):
        raise serializers.ValidationError({'categorias': ['Categoria removida. Atualize a página.']})
    if Inscricao.objects.filter(atleta=atleta, categoria_id__in=ids, status='ativa').exists():
        raise ConflitoInscricao('ja_inscrito', 'Você já está inscrito em uma das categorias selecionadas.')
    esgotadas = [c.pk for c in categorias if c.vagas is not None and c.inscricoes.filter(status='ativa').count() >= c.vagas]
    if esgotadas:
        raise ConflitoInscricao('sem_vagas', 'Não há vagas nas categorias selecionadas.', categorias_esgotadas=esgotadas)
    resultado = []
    for c in categorias:
        inscricao, _ = Inscricao.objects.update_or_create(categoria=c, atleta=atleta, defaults={
            'status': 'ativa', 'observacoes': dados['observacoes'], 'inscrito_por': atleta,
            'data_inscricao': timezone.now(), 'colocacao': None, 'destaque': ''})
        resultado.append(inscricao)
    nomes = ', '.join(c.nome for c in categorias)
    transaction.on_commit(lambda: enviar_email(atleta.email, 'Inscrição confirmada', f'{campeonato.nome}: {nomes}. Sua inscrição foi confirmada.'))
    return resultado


@transaction.atomic
def cancelar(atleta, pk):
    preparar_transacao()
    inscricao = get_object_or_404(Inscricao.objects.select_related('categoria'), pk=pk, atleta=atleta)
    c = Campeonato.objects.select_for_update().get(pk=inscricao.categoria.campeonato_id)
    Categoria.objects.select_for_update().get(pk=inscricao.categoria_id)
    conferir_prazo(c)
    inscricao.refresh_from_db()
    if inscricao.status == 'cancelada':
        return
    inscricao.status = 'cancelada'
    inscricao.save(update_fields=['status'])
    transaction.on_commit(lambda: enviar_email(atleta.email, 'Inscrição cancelada', f'Sua inscrição em {c.nome}, categoria {inscricao.categoria.nome}, foi cancelada.'))


class MinhasInscricoesView(generics.ListAPIView):
    permission_classes = [AtletaAtivo]
    serializer_class = SaidaInscricao
    pagination_class = None

    def get_queryset(self):
        return Inscricao.objects.filter(atleta=self.request.user).select_related('categoria__campeonato').order_by('-data_inscricao', '-pk')


class InscricaoCreateView(generics.GenericAPIView):
    permission_classes = [AtletaAtivo]
    serializer_class = EntradaInscricao

    def post(self, request):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        return Response(SaidaInscricao(inscrever(request.user, entrada.validated_data), many=True).data, status=201)


class InscricaoCancelarView(generics.GenericAPIView):
    permission_classes = [AtletaAtivo]

    def delete(self, request, pk):
        cancelar(request.user, pk)
        return Response(status=204)
