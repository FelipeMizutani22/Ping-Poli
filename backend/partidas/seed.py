"""Partidas de demonstração (08_DEMO_E_ENTREGA §1 · F3.3). Usa o gerador de placares da F3.2."""
import json
from datetime import datetime, time, timedelta

from django.utils import timezone

from nucleo.servicos import notificar
from .models import AdversarioExterno, Contestacao, HistoricoPartida, Partida, SetPartida
from .regras import gerar_placar_aleatorio

EXTERNOS = [
    ("Carlos Pereira", "ECP"), ("Mariana Okada", "Pinheiros"), ("Rodrigo Lopes", "Mackenzie"),
    ("Tatiana Ferraz", "FEI"), ("Paulo Nogueira", "Hebraica"), ("Juliana Prado", "Unicamp"),
]
PARTIDAS_DA_ANA = 35


def _momento(dia, hora=19):
    return timezone.make_aware(datetime.combine(dia, time(hora, 0)))


def _criar(atleta, dia, formato, sets, status="confirmada", adversario=None, externo=None,
           campeonato=None, categoria=None, fase="", registro=None):
    registro = registro or _momento(dia, 21)
    partida = Partida.objects.create(
        atleta=atleta, adversario=adversario, adversario_externo=externo,
        tipo_adversario="poli" if adversario else "externo",
        campeonato=campeonato, categoria=categoria, fase=fase, formato=formato, data_jogo=dia,
        status=status, data_registro=registro,
        data_confirmacao=registro + timedelta(hours=20) if status == "confirmada" else None,
    )
    SetPartida.objects.bulk_create(
        SetPartida(partida=partida, numero=n, pontos_atleta=s["pontos_atleta"], pontos_adversario=s["pontos_adversario"])
        for n, s in enumerate(sets, start=1)
    )
    return partida


def seed(rng, ctx):
    hoje = timezone.localdate()
    ana, bruno, carla = ctx["ana"], ctx["bruno"], ctx["carla"]
    marina = ctx["diretor"]
    atletas = ctx["atletas"]
    outros = [a for a in atletas if a != ana]
    jusp = ctx["campeonatos"]["jusp"]
    cat_jusp = ctx["categorias_jusp"]
    mulheres = ctx["mulheres"]
    externos = [AdversarioExterno.objects.create(nome=n, clube=c) for n, c in EXTERNOS]

    def sortear_dia(com_ana):
        while True:
            dia = hoje - timedelta(days=rng.randint(8, 364))
            if not (com_ana and dia.month == 7):  # a Ana não joga em julho (férias): lacuna no gráfico
                return dia

    def sortear_formato():
        return rng.choices([3, 5, 7], weights=[2, 7, 1])[0]

    total = rng.randint(70, 90) - 4  # as 4 partidas especiais da demo entram no fim
    criadas = []
    for i in range(total):
        com_ana = i < PARTIDAS_DA_ANA
        poli = rng.random() < 0.6
        formato = sortear_formato()

        if poli:
            if com_ana:
                rival = bruno if rng.random() < 0.35 else rng.choice(outros)
                atleta, adversario = (ana, rival) if rng.random() < 0.6 else (rival, ana)
            else:
                atleta, adversario = rng.sample(outros, 2)
            externo = None
        else:
            atleta = ana if com_ana else rng.choice(outros)
            adversario, externo = None, rng.choice(externos)

        # ~1 em cada 7 partidas é do JUSP (12–13/09); o resto é Amistoso/Treino
        campeonato = categoria = None
        fase = ""
        if rng.random() < 0.15 and not (com_ana and jusp.data_inicio.month == 7):
            dia = jusp.data_inicio + timedelta(days=rng.randint(0, 1))
            campeonato = jusp
            mesma_categoria = adversario is None or ((atleta.id in mulheres) == (adversario.id in mulheres))
            if mesma_categoria:
                categoria = cat_jusp["feminino"] if atleta.id in mulheres else cat_jusp["masculino"]
            fase = rng.choice(["Fase de grupos", "Oitavas de final", "Quartas de final"])
        else:
            dia = sortear_dia(com_ana)

        # A Ana vence um pouco mais do que perde; o resto é equilibrado
        if com_ana:
            ana_vence = rng.random() < 0.6
            vence_atleta = ana_vence if atleta == ana else not ana_vence
        else:
            vence_atleta = rng.random() < 0.5
        sets = gerar_placar_aleatorio(formato, rng, vence_atleta)
        criadas.append(_criar(atleta, dia, formato, sets, adversario=adversario, externo=externo,
                              campeonato=campeonato, categoria=categoria, fase=fase))

    # --- Partidas especiais para o roteiro da demo ---
    agora = timezone.now()

    # 2 pendentes em que a Ana é a adversária (aparecem em "Partidas pendentes" dela)
    for registrante, dias in ((bruno, 2), (carla, 1)):
        dia = hoje - timedelta(days=dias)
        p = _criar(registrante, dia, 5, gerar_placar_aleatorio(5, rng, True), status="pendente",
                   adversario=ana, registro=agora - timedelta(days=dias, hours=2))
        notificar(ana, "partida_pendente",
                  f"{registrante.nome} registrou uma partida contra você em {dia:%d/%m/%Y}. "
                  "Confirme ou conteste o resultado.", "/partidas/pendentes")
        criadas.append(p)

    # 1 contestada: Bruno × Carla, a Carla propõe outro placar
    dia = hoje - timedelta(days=3)
    contestada = _criar(bruno, dia, 5, [
        {"pontos_atleta": 11, "pontos_adversario": 8}, {"pontos_atleta": 9, "pontos_adversario": 11},
        {"pontos_atleta": 11, "pontos_adversario": 7}, {"pontos_atleta": 12, "pontos_adversario": 10},
    ], status="contestada", adversario=carla, registro=agora - timedelta(days=3))
    c = Contestacao.objects.create(
        partida=contestada, contestante=carla, data_contestacao=agora - timedelta(days=2),
        justificativa="O quarto set terminou 12 a 10 para mim, e eu venci o quinto set por 11 a 6.",
    )
    SetPartida.objects.bulk_create(
        SetPartida(partida=contestada, contestacao=c, numero=n, pontos_atleta=a, pontos_adversario=b)
        for n, (a, b) in enumerate([(11, 8), (9, 11), (11, 7), (10, 12), (6, 11)], start=1)
    )
    criadas.append(contestada)

    # 1 removida pela Diretoria, com o histórico gravado
    removida = _criar(rng.choice(outros), hoje - timedelta(days=20), 3,
                      gerar_placar_aleatorio(3, rng, True), adversario=None, externo=externos[0])
    HistoricoPartida.objects.create(
        partida=removida, alterado_por=marina, motivo="Partida registrada em duplicidade.",
        valores_anteriores=json.dumps({"status": "confirmada", "data_jogo": str(removida.data_jogo)}),
    )
    removida.status = "removida"
    removida.save(update_fields=["status"])
    criadas.append(removida)

    da_ana = sum(1 for p in criadas if ana.id in (p.atleta_id, p.adversario_id))
    return f"{len(criadas)} partidas ({da_ana} da Ana), 6 adversários externos, 2 pendentes, 1 contestada, 1 removida"
