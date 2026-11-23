"""Consultas que preparam as linhas usadas pelos cálculos de desempenho."""

from django.db.models import Prefetch, Q

from partidas.models import Partida, SetPartida
from partidas.regras import resultado


def linhas_do_atleta(
    atleta, inicio, fim, competicao="todas", tipo_adversario="todos"
):
    """Retorna partidas confirmadas na perspectiva do atleta.

    inicio e fim são datas já resolvidas pela camada chamadora.
    As permissões de acesso serão verificadas pela API.
    """
    if inicio > fim:
        raise ValueError("A data final não pode ser anterior à inicial.")

    if tipo_adversario not in ("todos", "poli", "externo"):
        raise ValueError("Tipo de adversário inválido.")

    partidas = Partida.objects.filter(
        Q(atleta_id=atleta.pk)
        | Q(tipo_adversario="poli", adversario_id=atleta.pk),
        status="confirmada",
        data_jogo__range=(inicio, fim),
    )

    if competicao == "amistoso":
        partidas = partidas.filter(campeonato__isnull=True)
    elif competicao != "todas":
        try:
            campeonato_id = int(competicao)
        except (TypeError, ValueError):
            raise ValueError("Competição inválida.") from None
        if campeonato_id <= 0:
            raise ValueError("Competição inválida.")
        partidas = partidas.filter(campeonato_id=campeonato_id)

    if tipo_adversario != "todos":
        partidas = partidas.filter(tipo_adversario=tipo_adversario)

    partidas = (
        partidas.select_related(
            "atleta", "adversario", "adversario_externo", "campeonato"
        )
        .prefetch_related(
            Prefetch(
                "sets",
                queryset=SetPartida.objects.filter(
                    contestacao__isnull=True
                ).order_by("numero"),
                to_attr="sets_para_desempenho",
            )
        )
        .order_by("data_jogo", "id")
    )

    return [_linha_da_partida(partida, atleta.pk) for partida in partidas]


def _linha_da_partida(partida, atleta_id):
    placar = resultado([
        {
            "pontos_atleta": s.pontos_atleta,
            "pontos_adversario": s.pontos_adversario,
        }
        for s in partida.sets_para_desempenho
    ])

    registrante = partida.atleta_id == atleta_id
    lado_pro = "atleta" if registrante else "adversario"
    lado_contra = "adversario" if registrante else "atleta"

    if not registrante:
        adversario = partida.atleta
    elif partida.tipo_adversario == "poli":
        adversario = partida.adversario
    else:
        adversario = partida.adversario_externo

    return {
        "partida_id": partida.pk,
        "data": partida.data_jogo,
        "campeonato_id": partida.campeonato_id,
        "competicao": (
            partida.campeonato.nome
            if partida.campeonato_id
            else "Amistoso/Treino"
        ),
        "tipo_adversario": partida.tipo_adversario,
        "adversario_id": adversario.pk,
        "adversario_nome": adversario.nome,
        "sets_pro": placar[f"sets_{lado_pro}"],
        "sets_contra": placar[f"sets_{lado_contra}"],
        "pontos_pro": placar[f"pontos_{lado_pro}"],
        "pontos_contra": placar[f"pontos_{lado_contra}"],
        "venceu": placar["vencedor"] == lado_pro,
    }



def primeira_data_do_atleta(atleta, hoje):
    """Primeiro jogo confirmado, em qualquer perspectiva, até hoje."""
    return Partida.objects.filter(
        Q(atleta_id=atleta.pk) | Q(tipo_adversario='poli', adversario_id=atleta.pk),
        status='confirmada', data_jogo__lte=hoje,
    ).order_by('data_jogo').values_list('data_jogo', flat=True).first()


def colocacoes_do_atleta(atleta, inicio, fim, competicao='todas'):
    """Resultados de inscrições ativas, pela data final do campeonato.

    Tipo de adversário não se aplica à colocação de uma categoria.
    """
    from competicoes.models import Inscricao

    if competicao == 'amistoso':
        return []
    inscricoes = Inscricao.objects.filter(
        atleta=atleta, status='ativa', colocacao__isnull=False,
        categoria__campeonato__data_fim__range=(inicio, fim),
    ).exclude(categoria__campeonato__status='cancelado')
    if competicao != 'todas':
        inscricoes = inscricoes.filter(categoria__campeonato_id=int(competicao))
    return [
        {
            'campeonato': item.categoria.campeonato.nome,
            'categoria': item.categoria.nome, 'colocacao': item.colocacao,
            'destaque': item.destaque, 'data': item.categoria.campeonato.data_fim,
        }
        for item in inscricoes.select_related('categoria__campeonato').order_by(
            '-categoria__campeonato__data_fim', 'categoria__nome', 'id'
        )
    ]


def primeira_data_da_equipe(hoje):
    return Partida.objects.filter(status='confirmada', data_jogo__lte=hoje).order_by(
        'data_jogo').values_list('data_jogo', flat=True).first()


def linhas_da_equipe(inicio, fim, competicao='todas'):
    """Duas consultas para toda a equipe, incluindo o histórico de inativos."""
    partidas = Partida.objects.filter(status='confirmada', data_jogo__range=(inicio, fim))
    if competicao == 'amistoso':
        partidas = partidas.filter(campeonato__isnull=True)
    elif competicao != 'todas':
        partidas = partidas.filter(campeonato_id=int(competicao))
    partidas = partidas.select_related('atleta', 'adversario', 'adversario_externo', 'campeonato').prefetch_related(
        Prefetch('sets', queryset=SetPartida.objects.filter(contestacao__isnull=True).order_by('numero'),
                 to_attr='sets_para_desempenho'))
    grupos = {}
    for partida in partidas:
        atletas = [partida.atleta]
        if partida.tipo_adversario == 'poli':
            atletas.append(partida.adversario)
        for atleta in atletas:
            grupo = grupos.setdefault(atleta.pk, {
                'atleta': {'id': atleta.pk, 'nome': atleta.nome, 'nusp': atleta.nusp}, 'linhas': []})
            grupo['linhas'].append(_linha_da_partida(partida, atleta.pk))
    return list(grupos.values())


def confronto_entre(a, b, inicio, fim, competicao='todas'):
    """Jogos do par em ambas as orientações; sets sempre na perspectiva de A."""
    pares = Partida.objects.filter(
        Q(atleta=a, adversario=b) | Q(atleta=b, adversario=a),
        tipo_adversario='poli', data_jogo__range=(inicio, fim))
    if competicao == 'amistoso':
        pares = pares.filter(campeonato__isnull=True)
    elif competicao != 'todas':
        pares = pares.filter(campeonato_id=int(competicao))
    pendentes = pares.filter(status='pendente').count()
    partidas = pares.filter(status='confirmada').select_related(
        'atleta', 'adversario', 'campeonato').prefetch_related(Prefetch(
            'sets', queryset=SetPartida.objects.filter(contestacao__isnull=True).order_by('numero'),
            to_attr='sets_para_desempenho')).order_by('data_jogo', 'pk')
    linhas, sets = [], {}
    for partida in partidas:
        linhas.append(_linha_da_partida(partida, a.pk))
        direto = partida.atleta_id == a.pk
        sets[partida.pk] = [{'numero': s.numero,
            'pontos_atleta': s.pontos_atleta if direto else s.pontos_adversario,
            'pontos_adversario': s.pontos_adversario if direto else s.pontos_atleta}
            for s in partida.sets_para_desempenho]
    return linhas, sets, pendentes
