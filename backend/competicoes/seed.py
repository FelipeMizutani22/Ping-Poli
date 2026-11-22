"""Campeonatos, categorias e inscrições de demonstração (08_DEMO_E_ENTREGA §1 · F4.4)."""
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from .models import Campeonato, Categoria, Inscricao

MULHERES = {"ana.lima@usp.br", "carla.mendes@usp.br", "elisa.tanaka@usp.br",
            "gabriela.nunes@usp.br", "marina.souza@usp.br"}


def _quando(dia, hora=9):
    return timezone.make_aware(datetime.combine(dia, time(hora, 0)))


def _inscrever(categoria, atleta, **extra):
    return Inscricao.objects.create(categoria=categoria, atleta=atleta, inscrito_por=atleta, **extra)


def seed(rng, ctx):
    marina = ctx["diretor"]
    usuarios = ctx["usuarios"]
    atletas = ctx["atletas"]
    mulheres = [a for a in atletas if a.email in MULHERES]
    homens = [a for a in atletas if a.email not in MULHERES]
    agora = timezone.now()

    # 1. JUSP 2026: finalizado (set/2026), com colocações (Ana 3ª no Feminino, "Bronze")
    jusp = Campeonato.objects.create(
        nome="JUSP 2026", organizador="FUPE", local_campeonato="CEPEUSP – Ginásio",
        data_inicio=date(2026, 9, 12), data_fim=date(2026, 9, 13),
        abertura_inscricoes=_quando(date(2026, 8, 1)), encerramento_inscricoes=_quando(date(2026, 9, 5), 23),
        status=Campeonato.Status.FINALIZADO, criado_por=marina,
    )
    jusp_masc = Categoria.objects.create(campeonato=jusp, nome="Masculino A", vagas=16)
    jusp_fem = Categoria.objects.create(campeonato=jusp, nome="Feminino", vagas=8)
    for pos, atleta in enumerate(homens, start=1):
        _inscrever(jusp_masc, atleta, colocacao=pos if pos <= 4 else None)
    ordem_fem = [usuarios["carla.mendes@usp.br"], usuarios["elisa.tanaka@usp.br"], usuarios["ana.lima@usp.br"]]
    ordem_fem += [a for a in mulheres if a not in ordem_fem]
    destaques = {1: "Ouro", 2: "Prata", 3: "Bronze"}
    for pos, atleta in enumerate(ordem_fem, start=1):
        _inscrever(jusp_fem, atleta, colocacao=pos if pos <= 4 else None, destaque=destaques.get(pos, ""))

    # 2. Copa Poli: inscrições abertas (abriu há 5 dias, fecha daqui a 10, jogos em 05–06/12)
    copa = Campeonato.objects.create(
        nome="Copa Poli de Tênis de Mesa", organizador="Equipe de Tênis de Mesa Poli-USP",
        local_campeonato="CEPEUSP – Ginásio", data_inicio=date(2026, 12, 5), data_fim=date(2026, 12, 6),
        abertura_inscricoes=agora - timedelta(days=5), encerramento_inscricoes=agora + timedelta(days=10),
        valor_inscricao=20, status=Campeonato.Status.INSCRICOES_ABERTAS, criado_por=marina,
    )
    copa_masc_a = Categoria.objects.create(campeonato=copa, nome="Masculino A", vagas=16)
    Categoria.objects.create(campeonato=copa, nome="Masculino B", vagas=None)
    copa_fem = Categoria.objects.create(campeonato=copa, nome="Feminino", vagas=2)
    Categoria.objects.create(campeonato=copa, nome="Duplas Mistas", vagas=8)
    for atleta in (usuarios["bruno.kato@usp.br"], usuarios["diego.alves@usp.br"]):
        _inscrever(copa_masc_a, atleta)
    for atleta in (usuarios["carla.mendes@usp.br"], usuarios["elisa.tanaka@usp.br"]):  # Feminino esgotado
        _inscrever(copa_fem, atleta)
    # A Ana NÃO está inscrita em nada da Copa Poli (ela se inscreve nas Duplas Mistas durante a demo).

    # 3. Torneio Interfaculdades 2027: planejado
    inter = Campeonato.objects.create(
        nome="Torneio Interfaculdades 2027", organizador="DCE-USP", local_campeonato="CEPEUSP – Ginásio",
        data_inicio=date(2027, 3, 20), data_fim=date(2027, 3, 21),
        abertura_inscricoes=_quando(date(2027, 2, 1)), encerramento_inscricoes=_quando(date(2027, 3, 10), 23),
        status=Campeonato.Status.PLANEJADO, criado_por=marina,
    )
    Categoria.objects.create(campeonato=inter, nome="Masculino", vagas=32)
    Categoria.objects.create(campeonato=inter, nome="Feminino", vagas=16)

    ctx["campeonatos"] = {"jusp": jusp, "copa": copa, "interfaculdades": inter}
    ctx["categorias_jusp"] = {"masculino": jusp_masc, "feminino": jusp_fem}
    ctx["mulheres"] = {a.id for a in mulheres}
    return "3 campeonatos (JUSP finalizado, Copa Poli com inscrições abertas, Interfaculdades planejado)"
