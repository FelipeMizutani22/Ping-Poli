"""Gestão de inscrições e resultados exclusiva da diretoria (UC14)."""
from collections import Counter
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.response import Response
from contas.permissoes import Diretor
from nucleo.servicos import auditar, enviar_email, notificar
from .models import Campeonato, Categoria, Inscricao
from .inscricoes import ConflitoInscricao, preparar_transacao, SaidaInscricao


class InscritoSerializer(SaidaInscricao):
    atleta = serializers.SerializerMethodField()

    class Meta(SaidaInscricao.Meta):
        fields = SaidaInscricao.Meta.fields + ['atleta', 'observacoes']

    def get_atleta(self, obj):
        return {'id': obj.atleta_id, 'nome': obj.atleta.nome, 'nusp': obj.atleta.nusp,
                'curso': obj.atleta.curso.nome if obj.atleta.curso_id else ''}


def inscritos(campeonato):
    return Inscricao.objects.filter(categoria__campeonato=campeonato, status='ativa').select_related(
        'atleta__curso', 'categoria__campeonato').order_by('categoria__nome', 'atleta__nome', 'pk')


def lista_gestao(campeonato):
    lista = list(inscritos(campeonato))
    grupos = []
    for categoria in campeonato.categorias.order_by('nome', 'pk'):
        itens = [i for i in lista if i.categoria_id == categoria.pk]
        grupos.append({'id': categoria.pk, 'nome': categoria.nome, 'vagas': categoria.vagas,
            'total_inscritos': len(itens), 'vagas_restantes': None if categoria.vagas is None else max(0, categoria.vagas - len(itens)),
            'inscricoes': InscritoSerializer(itens, many=True).data})
    return {'campeonato': {'id': campeonato.pk, 'nome': campeonato.nome, 'status': campeonato.status,
        'data_inicio': campeonato.data_inicio},
        'pode_registrar_resultados': campeonato.status != 'cancelado' and campeonato.data_inicio <= timezone.localdate(),
        'categorias': grupos}


class ResultadoEntrada(serializers.Serializer):
    colocacao = serializers.IntegerField(min_value=1, max_value=32767, allow_null=True, required=False)
    destaque = serializers.CharField(max_length=50, allow_blank=True, required=False)
    confirmar_empate = serializers.BooleanField(default=False)

    def validate(self, dados):
        if 'colocacao' not in dados and 'destaque' not in dados:
            raise serializers.ValidationError('Informe a colocação ou o destaque.')
        return dados


class ResultadoItem(ResultadoEntrada):
    id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)


class ResultadosEntrada(serializers.Serializer):
    resultados = ResultadoItem(many=True, allow_empty=False)
    confirmar_empate = serializers.BooleanField(default=False)

    def validate_resultados(self, itens):
        ids = [i['id'] for i in itens]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Uma inscrição não pode aparecer duas vezes.')
        return itens


@transaction.atomic
def salvar_resultados(campeonato_id, itens, autor, confirmar_empate=False):
    preparar_transacao()
    campeonato = get_object_or_404(Campeonato.objects.select_for_update(), pk=campeonato_id)
    if campeonato.status == 'cancelado' or campeonato.data_inicio > timezone.localdate():
        raise ConflitoInscricao('resultados_indisponiveis', 'Resultados só podem ser registrados a partir do início de um campeonato não cancelado.')
    list(Categoria.objects.select_for_update().filter(campeonato=campeonato).order_by('pk'))
    atuais = list(inscritos(campeonato).select_for_update(of=('self',)))
    por_id = {i.pk: i for i in atuais}
    if any(item['id'] not in por_id for item in itens):
        raise serializers.ValidationError({'resultados': ['Inscrição inválida, cancelada ou pertencente a outro campeonato. Atualize a lista.']})
    alteracoes = {item['id']: item for item in itens}
    categorias_alteradas = {por_id[item['id']].categoria_id for item in itens if 'colocacao' in item and item['colocacao'] != por_id[item['id']].colocacao}
    contagens = Counter((i.categoria_id, alteracoes.get(i.pk, {}).get('colocacao', i.colocacao)) for i in atuais)
    empates = [{'categoria': categoria, 'colocacao': colocacao} for (categoria, colocacao), total in contagens.items()
               if colocacao is not None and total > 1 and categoria in categorias_alteradas]
    if empates and not confirmar_empate:
        raise ConflitoInscricao('confirmar_empate', 'Há colocações repetidas na mesma categoria. Confirma que são empates?', empates=empates)
    for item in itens:
        inscricao = por_id[item['id']]
        anterior = {'colocacao': inscricao.colocacao, 'destaque': inscricao.destaque}
        novo = {campo: item.get(campo, anterior[campo]) for campo in anterior}
        if anterior == novo:
            continue
        inscricao.colocacao, inscricao.destaque = novo['colocacao'], novo['destaque']
        inscricao.save(update_fields=['colocacao', 'destaque'])
        auditar('inscricao', inscricao.pk, 'registrar_resultado', autor, anterior=anterior, novo=novo)
    return campeonato


class ManualEntrada(serializers.Serializer):
    atleta = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    categorias = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=9223372036854775807), allow_empty=False)
    observacoes = serializers.CharField(max_length=300, allow_blank=True, default='')

    def validate_categorias(self, ids):
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Selecione cada categoria uma única vez.')
        return ids


@transaction.atomic
def incluir_manual(campeonato_id, dados, autor):
    preparar_transacao()
    campeonato = get_object_or_404(Campeonato.objects.select_for_update(), pk=campeonato_id)
    if campeonato.status == 'cancelado':
        raise ConflitoInscricao('campeonato_cancelado', 'Não é possível incluir inscrições em um campeonato cancelado.')
    atleta = get_object_or_404(get_user_model().objects.select_for_update(), pk=dados['atleta'], situacao='ativa')
    categorias = list(Categoria.objects.select_for_update().filter(campeonato=campeonato, pk__in=dados['categorias']).order_by('pk'))
    if len(categorias) != len(dados['categorias']):
        raise serializers.ValidationError({'categorias': ['Selecione categorias deste campeonato.']})
    if Inscricao.objects.filter(atleta=atleta, categoria__in=categorias, status='ativa').exists():
        raise ConflitoInscricao('ja_inscrito', 'O atleta já está inscrito em uma das categorias selecionadas.')
    esgotadas = [c.pk for c in categorias if c.vagas is not None and c.inscricoes.filter(status='ativa').count() >= c.vagas]
    if esgotadas:
        raise ConflitoInscricao('sem_vagas', 'Não há vagas nas categorias selecionadas.', categorias_esgotadas=esgotadas)
    for categoria in categorias:
        inscricao = Inscricao.objects.filter(categoria=categoria, atleta=atleta).first()
        anterior = None if inscricao is None else {'status': inscricao.status, 'colocacao': inscricao.colocacao, 'destaque': inscricao.destaque}
        inscricao, _ = Inscricao.objects.update_or_create(categoria=categoria, atleta=atleta, defaults={
            'status': 'ativa', 'inscrito_por': autor, 'data_inscricao': timezone.now(),
            'observacoes': dados['observacoes'], 'colocacao': None, 'destaque': ''})
        auditar('inscricao', inscricao.pk, 'incluir_manualmente', autor, anterior=anterior, novo={'status': 'ativa'})
    mensagem = f'Inscrição confirmada pela diretoria em {campeonato.nome}: ' + ', '.join(c.nome for c in categorias)
    notificar(atleta, 'inscricao_confirmada', mensagem, '/inscricoes')
    transaction.on_commit(lambda: enviar_email(atleta.email, 'Inscrição confirmada', mensagem))
    return campeonato


class RemocaoEntrada(serializers.Serializer):
    motivo = serializers.CharField(min_length=10, max_length=300)


@transaction.atomic
def remover_manual(pk, motivo, autor):
    preparar_transacao()
    inscricao = get_object_or_404(Inscricao.objects.select_related('categoria__campeonato', 'atleta'), pk=pk)
    Campeonato.objects.select_for_update().get(pk=inscricao.categoria.campeonato_id)
    Categoria.objects.select_for_update().get(pk=inscricao.categoria_id)
    inscricao.refresh_from_db()
    if inscricao.status == 'cancelada':
        return
    inscricao.status = 'cancelada'
    inscricao.save(update_fields=['status'])
    auditar('inscricao', pk, 'remover_manualmente', autor, justificativa=motivo, anterior={'status': 'ativa'}, novo={'status': 'cancelada'})
    mensagem = f'Inscrição em {inscricao.categoria.campeonato.nome}, categoria {inscricao.categoria.nome}, cancelada pela diretoria. Motivo: {motivo}'
    transaction.on_commit(lambda: enviar_email(inscricao.atleta.email, 'Inscrição cancelada', mensagem))


class GestaoInscricoesView(generics.GenericAPIView):
    permission_classes = [Diretor]
    serializer_class = ManualEntrada

    def get(self, request, pk):
        return Response(lista_gestao(get_object_or_404(Campeonato, pk=pk)))

    def post(self, request, pk):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        campeonato = incluir_manual(pk, entrada.validated_data, request.user)
        return Response(lista_gestao(campeonato), status=201)


class ResultadosView(generics.GenericAPIView):
    permission_classes = [Diretor]
    serializer_class = ResultadosEntrada

    def patch(self, request, pk):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        d = entrada.validated_data
        campeonato = salvar_resultados(pk, d['resultados'], request.user, d['confirmar_empate'])
        return Response(lista_gestao(campeonato))


class ResultadoView(generics.GenericAPIView):
    permission_classes = [Diretor]
    serializer_class = ResultadoEntrada

    def patch(self, request, pk):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        inscricao = get_object_or_404(Inscricao.objects.select_related('categoria'), pk=pk)
        d = entrada.validated_data
        salvar_resultados(inscricao.categoria.campeonato_id, [{'id': pk, **d}], request.user, d['confirmar_empate'])
        return Response(InscritoSerializer(inscritos(inscricao.categoria.campeonato_id).get(pk=pk)).data)


class RemoverInscricaoView(generics.GenericAPIView):
    permission_classes = [Diretor]
    serializer_class = RemocaoEntrada

    def post(self, request, pk):
        entrada = self.get_serializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        remover_manual(pk, entrada.validated_data['motivo'], request.user)
        return Response(status=204)
