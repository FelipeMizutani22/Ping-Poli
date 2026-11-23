"""Gravações atômicas e ciclo de vida dos campeonatos."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError
from avisos.models import Aviso
from nucleo.servicos import auditar, enviar_email, notificar, notificar_diretores
from .models import Campeonato, Categoria, Inscricao


class ConflitoCampeonato(APIException):
    status_code = 409

    def __init__(self, mensagem, codigo, **extra):
        super().__init__({'detail': mensagem, 'codigo': codigo, **extra})


def _abertura(campeonato):
    for atleta in get_user_model().objects.filter(situacao='ativa'):
        notificar(atleta, 'inscricoes_abertas', f'Inscrições abertas: {campeonato.nome}',
                  link=f'/campeonatos/{campeonato.pk}')


def _sincronizar(campeonato, agora):
    """Avança todas as etapas vencidas, sem regredir estados terminais."""
    anterior = campeonato.status
    if campeonato.status == 'planejado' and agora >= campeonato.abertura_inscricoes:
        campeonato.status = 'inscricoes_abertas'
        # Não anunciar inscrições já encerradas ao recuperar execuções antigas.
        if agora < campeonato.encerramento_inscricoes:
            _abertura(campeonato)
    if campeonato.status == 'inscricoes_abertas' and agora >= campeonato.encerramento_inscricoes:
        campeonato.status = 'inscricoes_encerradas'
    if campeonato.status == 'inscricoes_encerradas' and timezone.localdate(agora) > campeonato.data_fim:
        campeonato.status = 'finalizado'
        notificar_diretores('campeonato_finalizado', f'Registre os resultados: {campeonato.nome}',
                            link=f'/campeonatos/{campeonato.pk}')
    if anterior != campeonato.status:
        campeonato.save(update_fields=['status'])
        return 1
    return 0


@transaction.atomic
def sincronizar_status(agora=None):
    """Retorna quantos campeonatos mudaram. Repetições não duplicam notificações."""
    agora = agora or timezone.now()
    pendentes = Campeonato.objects.select_for_update().filter(
        Q(status='planejado', abertura_inscricoes__lte=agora)
        | Q(status='inscricoes_abertas', encerramento_inscricoes__lte=agora)
        | Q(status='inscricoes_encerradas', data_fim__lt=timezone.localdate(agora)))
    return sum(_sincronizar(campeonato, agora) for campeonato in pendentes)


def _duplicidade(dados, campeonato=None):
    nome = dados.get('nome', campeonato.nome if campeonato else '')
    inicio = dados.get('data_inicio', campeonato.data_inicio if campeonato else None)
    semelhantes = Campeonato.objects.filter(nome__iexact=nome, data_inicio=inicio)
    if campeonato:
        semelhantes = semelhantes.exclude(pk=campeonato.pk)
    semelhante = semelhantes.first()
    if semelhante and not dados.get('confirmar_duplicada', False):
        raise ConflitoCampeonato('Já existe campeonato com esse nome e data. Confirme para salvar mesmo assim.',
                                 'possivel_duplicada', campeonato_id=semelhante.pk)


def _emails_inscritos(campeonato, assunto, mensagem):
    emails = list(Inscricao.objects.filter(categoria__campeonato=campeonato, status='ativa')
                  .order_by().values_list('atleta__email', flat=True).distinct())
    def enviar():
        for email in emails:
            enviar_email(email, assunto, mensagem)
    transaction.on_commit(enviar)


@transaction.atomic
def criar_campeonato(autor, dados):
    dados = dict(dados)
    _duplicidade(dados)
    dados.pop('confirmar_duplicada', None)
    anunciar = dados.pop('anunciar', True)
    categorias = dados.pop('categorias')
    dados.pop('status', None)
    campeonato = Campeonato.objects.create(criado_por=autor, status='planejado', **dados)
    for categoria in categorias:
        Categoria.objects.create(campeonato=campeonato, **categoria)
    _sincronizar(campeonato, timezone.now())
    if anunciar:
        Aviso.objects.create(autor=autor, categoria='campeonato', titulo=f'Campeonato: {campeonato.nome}'[:100],
            conteudo=(f'{campeonato.nome}: de {campeonato.data_inicio:%d/%m/%Y} a {campeonato.data_fim:%d/%m/%Y}. '
                      f'Local: {campeonato.local_campeonato}. Inscrições de '
                      f'{timezone.localtime(campeonato.abertura_inscricoes):%d/%m/%Y %H:%M} a '
                      f'{timezone.localtime(campeonato.encerramento_inscricoes):%d/%m/%Y %H:%M}.'))
    return campeonato


def _editar_categorias(campeonato, itens):
    atuais = {c.pk: c for c in campeonato.categorias.select_for_update()}
    ids = {item['id'] for item in itens if 'id' in item}
    if not ids.issubset(atuais):
        raise ValidationError({'categorias': ['Categoria não pertence a este campeonato.']})
    removidas = [c for pk, c in atuais.items() if pk not in ids]
    for categoria in removidas:
        if categoria.inscricoes.exists() or categoria.partidas.exists():
            raise ConflitoCampeonato('Não remova categorias com inscrições ou partidas. Preserve o histórico.',
                                     'categoria_vinculada')
    for item in itens:
        if 'id' in item and item.get('vagas') is not None:
            total = atuais[item['id']].inscricoes.filter(status='ativa').count()
            if item['vagas'] < total:
                raise ValidationError({'categorias': ['As vagas não podem ser menores que as inscrições ativas.']})
    for categoria in removidas:
        categoria.delete()
    # Nomes temporários permitem trocar nomes de duas categorias sem violar a unicidade.
    # Não ficam visíveis fora da transação.
    from uuid import uuid4
    for pk in ids:
        Categoria.objects.filter(pk=pk).update(nome=f'__edicao_{uuid4().hex}')
    for item in itens:
        valores = {campo: item.get(campo) for campo in ('nome', 'vagas')}
        if 'id' in item:
            Categoria.objects.filter(pk=item['id']).update(**valores)
        else:
            Categoria.objects.create(campeonato=campeonato, **valores)


@transaction.atomic
def editar_campeonato(campeonato_id, dados, autor):
    campeonato = Campeonato.objects.select_for_update().get(pk=campeonato_id)
    # Revalida com a versão bloqueada, inclusive quando o PATCH contém só uma data.
    from .serializers import CampeonatoEntradaSerializer
    entrada = CampeonatoEntradaSerializer(campeonato, data=dados, partial=True)
    entrada.is_valid(raise_exception=True)
    dados = dict(entrada.validated_data)
    _duplicidade(dados, campeonato)
    dados.pop('confirmar_duplicada', None)
    dados.pop('anunciar', None)
    novo_status = dados.pop('status', campeonato.status)
    agora = timezone.now()
    if novo_status != campeonato.status:
        permitidas = {'planejado': 'inscricoes_abertas', 'inscricoes_abertas': 'inscricoes_encerradas'}
        if permitidas.get(campeonato.status) != novo_status:
            raise ValidationError({'status': ['Transição inválida. Use a ação de cancelamento para cancelar.']})
        if novo_status == 'inscricoes_abertas':
            if agora >= campeonato.encerramento_inscricoes:
                raise ValidationError({'status': ['O prazo de inscrição já terminou.']})
            dados['abertura_inscricoes'] = agora
        else:
            if agora <= campeonato.abertura_inscricoes:
                raise ValidationError({'status': ['O encerramento precisa ser posterior à abertura.']})
            dados['encerramento_inscricoes'] = agora
        if any(campo in dados for campo in ('data_inicio', 'data_fim')):
            raise ValidationError({'status': ['Altere as datas e o status em operações separadas.']})
    categorias = dados.pop('categorias', None)
    mudou_agenda = any(c in dados and dados[c] != getattr(campeonato, c)
                      for c in ('data_inicio', 'data_fim', 'local_campeonato'))
    for campo, valor in dados.items():
        setattr(campeonato, campo, valor)
    # Revalida também as datas ajustadas pela antecipação manual.
    validacao = CampeonatoEntradaSerializer(campeonato, data={}, partial=True)
    validacao.is_valid(raise_exception=True)
    if categorias is not None:
        _editar_categorias(campeonato, categorias)
    if novo_status != campeonato.status and novo_status == 'inscricoes_abertas':
        _abertura(campeonato)
    campeonato.status = novo_status
    campeonato.save()
    _sincronizar(campeonato, agora)
    if mudou_agenda:
        _emails_inscritos(campeonato, f'Alteração: {campeonato.nome}',
                         f'Confira a alteração de datas ou local do campeonato {campeonato.nome}: '
                         f'{campeonato.data_inicio:%d/%m/%Y} a {campeonato.data_fim:%d/%m/%Y}, {campeonato.local_campeonato}.')
    return campeonato


@transaction.atomic
def cancelar_campeonato(campeonato_id, autor, motivo):
    campeonato = Campeonato.objects.select_for_update().get(pk=campeonato_id)
    _sincronizar(campeonato, timezone.now())
    if campeonato.status == 'finalizado':
        raise ConflitoCampeonato('Campeonato finalizado não pode ser cancelado.', 'campeonato_finalizado')
    if campeonato.status == 'cancelado':
        return campeonato
    anterior = campeonato.status
    campeonato.status = 'cancelado'
    campeonato.save(update_fields=['status'])
    auditar('campeonato', campeonato.pk, 'cancelar', autor, justificativa=motivo,
            anterior={'status': anterior}, novo={'status': 'cancelado'})
    _emails_inscritos(campeonato, f'Cancelamento: {campeonato.nome}',
                     f'O campeonato {campeonato.nome} foi cancelado. Motivo: {motivo}')
    return campeonato
