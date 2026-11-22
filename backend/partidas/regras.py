"""
Regras do placar do tênis de mesa (UC15 e 05_REGRAS_DE_NEGOCIO §2).

Funções puras: não acessam o banco de dados. São usadas pelo serializer de
partidas, pelo seed_demo e pelos testes.

Cada set é um dicionário {"pontos_atleta": int, "pontos_adversario": int},
na ordem em que foi jogado. O número do set é a posição na lista (1, 2, 3...).
"""


def sets_para_vencer(formato):
    """Quantos sets um jogador precisa vencer. Ex.: melhor de 5 -> 3."""
    return (formato + 1) // 2


def validar_set(pontos_atleta, pontos_adversario, numero):
    """Devolve [] se o set é válido, ou uma lista com a mensagem do problema."""
    for pontos in (pontos_atleta, pontos_adversario):
        if not 0 <= pontos <= 99:
            return [f"Set {numero}: os pontos devem estar entre 0 e 99"]

    if pontos_atleta == pontos_adversario:
        return [f"Set {numero}: o set não pode terminar empatado"]

    vencedor = max(pontos_atleta, pontos_adversario)
    perdedor = min(pontos_atleta, pontos_adversario)
    diferenca = vencedor - perdedor

    if vencedor < 11 or diferenca < 2:
        return [f"Set {numero}: o vencedor precisa de 11 pontos com 2 de vantagem"]

    if vencedor > 11 and diferenca != 2:
        return [f"Set {numero}: acima de 11 pontos, a diferença deve ser exatamente 2"]

    return []


def validar_placar(sets, formato):
    """Devolve [] se o placar da partida é válido, ou a lista de todos os problemas."""
    alvo = sets_para_vencer(formato)

    if len(sets) > formato:
        return [f"Melhor de {formato} admite no máximo {formato} sets"]

    erros = []
    vitorias_atleta = 0
    vitorias_adversario = 0
    decidida_no_set = None

    for numero, s in enumerate(sets, start=1):
        if decidida_no_set is not None:
            erros.append(f"A partida já estava decidida no set {decidida_no_set}")
            break

        erros_do_set = validar_set(s["pontos_atleta"], s["pontos_adversario"], numero)
        if erros_do_set:
            erros.extend(erros_do_set)
            continue

        if s["pontos_atleta"] > s["pontos_adversario"]:
            vitorias_atleta += 1
        else:
            vitorias_adversario += 1

        if vitorias_atleta == alvo or vitorias_adversario == alvo:
            decidida_no_set = numero

    if not erros and decidida_no_set is None:
        erros.append(f"Nenhum jogador venceu {alvo} sets (melhor de {formato})")

    return erros


def resultado(sets):
    """Totais e vencedor de um placar que JÁ passou por validar_placar."""
    sets_atleta = sum(1 for s in sets if s["pontos_atleta"] > s["pontos_adversario"])
    sets_adversario = len(sets) - sets_atleta
    return {
        "sets_atleta": sets_atleta,
        "sets_adversario": sets_adversario,
        "vencedor": "atleta" if sets_atleta > sets_adversario else "adversario",
        "pontos_atleta": sum(s["pontos_atleta"] for s in sets),
        "pontos_adversario": sum(s["pontos_adversario"] for s in sets),
    }