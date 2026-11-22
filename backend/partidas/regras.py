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



def gerar_placar_aleatorio(formato, rng, vence_atleta):
    """
    Gera um placar SEMPRE válido, para o seed_demo (F3.3).

    rng: um random.Random(semente). Com a mesma semente, o seed sai igual toda vez.
    vence_atleta: True -> o registrante vence a partida; False -> o adversário vence.
    """
    alvo = sets_para_vencer(formato)
    sets_do_perdedor = rng.randint(0, alvo - 1)
    total = alvo + sets_do_perdedor

    # O último set é sempre do vencedor; os sets do perdedor ficam espalhados antes dele.
    posicoes_do_perdedor = set(rng.sample(range(total - 1), sets_do_perdedor))

    sets = []
    for i in range(total):
        pontos_vencedor, pontos_perdedor = _pontos_de_um_set(rng)
        atleta_venceu_o_set = (i not in posicoes_do_perdedor) == vence_atleta
        if atleta_venceu_o_set:
            sets.append({"pontos_atleta": pontos_vencedor, "pontos_adversario": pontos_perdedor})
        else:
            sets.append({"pontos_atleta": pontos_perdedor, "pontos_adversario": pontos_vencedor})
    return sets


def _pontos_de_um_set(rng):
    """Pontos (vencedor, perdedor) de um set válido: 80% normal (11 a 0–9), 20% prorrogação."""
    if rng.random() < 0.8:
        return 11, rng.randint(0, 9)
    perdedor = rng.randint(10, 14)
    return perdedor + 2, perdedor