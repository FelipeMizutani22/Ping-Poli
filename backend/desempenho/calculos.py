"""Cálculos de desempenho sobre listas de partidas, sem acesso ao banco."""

from datetime import date

def sequencia_atual(linhas):
    """Retorna a sequência mais recente de vitórias ou derrotas."""
    if not linhas:
        return None

    ordenadas = sorted(
        linhas,
        key=lambda linha: (linha["data"], linha["partida_id"]),
        reverse=True,
    )

    resultado_recente = ordenadas[0]["venceu"]
    quantidade = 0

    for linha in ordenadas:
        if linha["venceu"] != resultado_recente:
            break
        quantidade += 1

    return {
        "tipo": "V" if resultado_recente else "D",
        "quantidade": quantidade,
    }

def indicadores(linhas):
    """Calcula os totais do dashboard a partir das linhas do atleta."""
    partidas = len(linhas)
    vitorias = sum(1 for linha in linhas if linha["venceu"])
    derrotas = partidas - vitorias

    sets_pro = sum(linha["sets_pro"] for linha in linhas)
    sets_contra = sum(linha["sets_contra"] for linha in linhas)
    pontos_pro = sum(linha["pontos_pro"] for linha in linhas)
    pontos_contra = sum(linha["pontos_contra"] for linha in linhas)

    return {
        "partidas": partidas,
        "vitorias": vitorias,
        "derrotas": derrotas,
        "pct_vitorias": round(100 * vitorias / partidas, 1) if partidas else 0.0,
        "sets_pro": sets_pro,
        "sets_contra": sets_contra,
        "saldo_sets": sets_pro - sets_contra,
        "pontos_pro": pontos_pro,
        "pontos_contra": pontos_contra,
        "sequencia_atual": sequencia_atual(linhas),
    }

def evolucao_mensal(linhas, inicio, fim):
    """Retorna todos os meses do período, inclusive aqueles sem partidas."""
    if inicio > fim:
        raise ValueError("A data final não pode ser anterior à inicial.")

    meses = {}
    mes = inicio.replace(day=1)

    while mes <= fim:
        chave = mes.strftime("%Y-%m")
        meses[chave] = {
            "mes": chave,
            "partidas": 0,
            "vitorias": 0,
            "pct_vitorias": None,
        }

        if mes.month == 12:
            mes = date(mes.year + 1, 1, 1)
        else:
            mes = date(mes.year, mes.month + 1, 1)

    for linha in linhas:
        if inicio <= linha["data"] <= fim:
            chave = linha["data"].strftime("%Y-%m")
            resumo = meses[chave]
            resumo["partidas"] += 1
            if linha["venceu"]:
                resumo["vitorias"] += 1

    for resumo in meses.values():
        if resumo["partidas"]:
            resumo["pct_vitorias"] = round(
                100 * resumo["vitorias"] / resumo["partidas"], 1
            )

    return list(meses.values())

def por_competicao(linhas):
    """Agrupa vitórias e derrotas pelo identificador do campeonato."""
    grupos = {}

    for linha in linhas:
        campeonato_id = linha["campeonato_id"]

        if campeonato_id not in grupos:
            grupos[campeonato_id] = {
                "competicao": (
                    "Amistoso/Treino"
                    if campeonato_id is None
                    else linha["competicao"]
                ),
                "campeonato_id": campeonato_id,
                "vitorias": 0,
                "derrotas": 0,
            }

        if linha["venceu"]:
            grupos[campeonato_id]["vitorias"] += 1
        else:
            grupos[campeonato_id]["derrotas"] += 1

    return list(grupos.values())

def resolver_periodo(
    periodo="12m", *, hoje, inicio=None, fim=None, primeira_data=None
):
    """Resolve o período em duas datas, sem consultar o banco ou o relógio."""
    if periodo in ("3m", "6m", "12m"):
        quantidade = int(periodo[:-1])
        indice_mes = hoje.year * 12 + hoje.month - 1
        ano_inicial, mes_inicial = divmod(indice_mes - quantidade + 1, 12)
        return date(ano_inicial, mes_inicial + 1, 1), hoje

    if periodo == "tudo":
        # Sem histórico, usa o mês atual, que aparecerá sem partidas.
        inicio_historico = primeira_data or hoje.replace(day=1)
        if inicio_historico > hoje:
            raise ValueError("A primeira partida não pode estar no futuro.")
        return inicio_historico, hoje

    if periodo == "custom":
        if inicio is None or fim is None:
            raise ValueError("Informe a data inicial e a data final.")
        if inicio > fim:
            raise ValueError("A data final não pode ser anterior à inicial.")
        if fim > hoje:
            raise ValueError("A data final não pode estar no futuro.")
        return inicio, fim

    raise ValueError("Período inválido.")


def mais_enfrentados(linhas):
    """Retorna até cinco adversários, por quantidade de partidas e nome."""
    grupos = {}

    for linha in linhas:
        chave = (linha["tipo_adversario"], linha["adversario_id"])

        if chave not in grupos:
            grupos[chave] = {
                "adversario": {
                    "tipo": linha["tipo_adversario"],
                    "id": linha["adversario_id"],
                    "nome": linha["adversario_nome"],
                },
                "partidas": 0,
                "vitorias": 0,
                "derrotas": 0,
            }

        resumo = grupos[chave]
        resumo["partidas"] += 1
        if linha["venceu"]:
            resumo["vitorias"] += 1
        else:
            resumo["derrotas"] += 1

    ordenados = sorted(
        grupos.values(),
        key=lambda resumo: (
            -resumo["partidas"],
            resumo["adversario"]["nome"],
        ),
    )
    return ordenados[:5]


def recentes(linhas):
    """Retorna até dez partidas recentes, no ponto de vista do atleta."""
    ordenadas = sorted(
        linhas,
        key=lambda linha: (linha["data"], linha["partida_id"]),
        reverse=True,
    )

    return [
        {
            "partida_id": linha["partida_id"],
            "data": linha["data"],
            "competicao": linha["competicao"],
            "adversario": {
                "tipo": linha["tipo_adversario"],
                "id": linha["adversario_id"],
                "nome": linha["adversario_nome"],
            },
            "sets_pro": linha["sets_pro"],
            "sets_contra": linha["sets_contra"],
            "venceu": linha["venceu"],
            "placar": f'{linha["sets_pro"]}–{linha["sets_contra"]}',
        }
        for linha in ordenadas[:10]
    ]

def ranking_equipe(atletas_com_linhas):
    """Recebe itens com 'atleta' (resumo) e 'linhas' já filtradas."""
    ranking = []

    for item in atletas_com_linhas:
        resumo = indicadores(item["linhas"])
        if resumo["partidas"] < 5:
            continue

        ranking.append({
            "atleta": dict(item["atleta"]),
            "partidas": resumo["partidas"],
            "vitorias": resumo["vitorias"],
            "pct_vitorias": resumo["pct_vitorias"],
            "saldo_sets": resumo["saldo_sets"],
        })

    ranking.sort(key=lambda item: (
        -item["pct_vitorias"],
        -item["saldo_sets"],
        -item["partidas"],
        item["atleta"]["nome"],
    ))

    return [
        {"posicao": posicao, **item}
        for posicao, item in enumerate(ranking, start=1)
    ]


def partidas_por_mes(linhas, inicio, fim):
    """Conta jogos únicos, mesmo quando aparecem para os dois atletas."""
    unicas = {}
    for linha in linhas:
        unicas.setdefault(linha["partida_id"], linha)

    return [
        {"mes": mes["mes"], "partidas": mes["partidas"]}
        for mes in evolucao_mensal(list(unicas.values()), inicio, fim)
    ]

def confronto_direto(linhas, a, b, *, pendentes_entre_eles=0):
    """Calcula o confronto com linhas confirmadas na perspectiva de A.

    As linhas devem conter apenas jogos Poli entre A e B, já filtrados
    pelo período. A consulta ao banco será responsável por essa seleção.
    """
    if a["id"] == b["id"]:
        raise ValueError("Escolha um atleta diferente")

    ordenadas = sorted(
        linhas,
        key=lambda linha: (linha["data"], linha["partida_id"]),
    )

    # Cada chamada recebe uma única linha para reaproveitar o formato
    # PartidaPerspectiva, sem aplicar o limite de dez ao histórico.
    partidas = [recentes([linha])[0] for linha in ordenadas]

    linhas_b = [
        {
            **linha,
            "adversario_id": a["id"],
            "adversario_nome": a["nome"],
            "sets_pro": linha["sets_contra"],
            "sets_contra": linha["sets_pro"],
            "pontos_pro": linha["pontos_contra"],
            "pontos_contra": linha["pontos_pro"],
            "venceu": not linha["venceu"],
        }
        for linha in ordenadas
    ]

    resumo_a = indicadores(ordenadas)
    resumo_b = indicadores(linhas_b)

    def maior_vitoria(venceu_a):
        candidatas = [
            linha for linha in ordenadas
            if linha["venceu"] == venceu_a
        ]
        if not candidatas:
            return None

        maior = max(
            candidatas,
            key=lambda linha: (
                abs(linha["sets_pro"] - linha["sets_contra"]),
                linha["data"],
                linha["partida_id"],
            ),
        )
        # Até a maior vitória de B é exibida na perspectiva de A.
        return recentes([maior])[0]

    acumulado = []
    vitorias_a = 0
    vitorias_b = 0

    for linha in ordenadas:
        if linha["venceu"]:
            vitorias_a += 1
        else:
            vitorias_b += 1

        acumulado.append({
            "data": linha["data"],
            "vitorias_a": vitorias_a,
            "vitorias_b": vitorias_b,
        })

    return {
        "a": dict(a),
        "b": dict(b),
        "retrospecto": {
            "vitorias_a": resumo_a["vitorias"],
            "vitorias_b": resumo_b["vitorias"],
            "sets_a": resumo_a["sets_pro"],
            "sets_b": resumo_b["sets_pro"],
            "pontos_a": resumo_a["pontos_pro"],
            "pontos_b": resumo_b["pontos_pro"],
            "pct_a": resumo_a["pct_vitorias"],
            "pct_b": resumo_b["pct_vitorias"],
        },
        "ultima_partida": partidas[-1] if partidas else None,
        "maior_vitoria_a": maior_vitoria(True),
        "maior_vitoria_b": maior_vitoria(False),
        "partidas": partidas,
        "acumulado": acumulado,
        "indicadores_a": resumo_a,
        "indicadores_b": resumo_b,
        "pendentes_entre_eles": pendentes_entre_eles,
    }