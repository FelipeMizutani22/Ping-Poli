"""Usuários de teste do PingPoli (todos com a senha "pingpoli123")."""
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Curso

SENHA = "pingpoli123"

# (e-mail, nome, papel, situacao, curso, ano de ingresso, mão dominante)
USUARIOS = [
    ("marina.souza@usp.br", "Marina Souza", "diretor", "ativa", "Engenharia Mecatrônica", 2022, "destro"),
    ("rafael.costa@usp.br", "Rafael Costa", "diretor", "ativa", "Engenharia Civil", 2021, "destro"),
    ("ana.lima@usp.br", "Ana Lima", "atleta", "ativa", "Engenharia de Computação", 2023, "destro"),
    ("bruno.kato@usp.br", "Bruno Kato", "atleta", "ativa", "Engenharia Elétrica", 2022, "canhoto"),
    ("carla.mendes@usp.br", "Carla Mendes", "atleta", "ativa", "Engenharia de Produção", 2024, "destro"),
    ("diego.alves@usp.br", "Diego Alves", "atleta", "ativa", "Engenharia Mecânica", 2023, "destro"),
    ("elisa.tanaka@usp.br", "Elisa Tanaka", "atleta", "ativa", "Engenharia Química", 2025, "canhoto"),
    ("felipe.ramos@usp.br", "Felipe Ramos", "atleta", "ativa", "Engenharia Naval", 2022, "destro"),
    ("gabriela.nunes@usp.br", "Gabriela Nunes", "atleta", "ativa", "Engenharia Ambiental", 2024, "destro"),
    ("henrique.sato@usp.br", "Henrique Sato", "atleta", "ativa", "Engenharia de Materiais", 2021, "destro"),
    ("igor.pereira@usp.br", "Igor Pereira", "atleta", "inativa", "Engenharia de Minas", 2020, "destro"),
    ("julia.martins@usp.br", "Júlia Martins", "atleta", "pendente", "Engenharia Mecatrônica", 2025, ""),
    ("lucas.rocha@usp.br", "Lucas Rocha", "atleta", "recusada", "Engenharia de Petróleo", 2025, ""),
]


def seed(rng, ctx):
    Atleta = get_user_model()
    agora = timezone.now()
    cursos = {c.nome: c for c in Curso.objects.all()}
    criados = {}

    for i, (email, nome, papel, situacao, curso, ano, mao) in enumerate(USUARIOS, start=1):
        campos = dict(
            nome=nome, nusp=15500000 + i, curso=cursos[curso], ano_ingresso=ano,
            telefone=f"(11) 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
            mao_dominante=mao, papel=papel, situacao=situacao,
            data_solicitacao=agora - timezone.timedelta(days=rng.randint(30, 400)),
        )
        if email == "marina.souza@usp.br":
            criados[email] = Atleta.objects.create_superuser(email, SENHA, **campos)
        else:
            criados[email] = Atleta.objects.create_user(email, SENHA, **campos)

    marina = criados["marina.souza@usp.br"]
    for atleta in criados.values():
        if atleta.situacao != "pendente" and atleta != marina:
            atleta.avaliado_por = marina
            atleta.data_avaliacao = atleta.data_solicitacao + timezone.timedelta(days=2)
            if atleta.situacao == "recusada":
                atleta.motivo_recusa = "Não é aluno da Poli-USP."
            atleta.save()
    pendente = criados["julia.martins@usp.br"]
    pendente.data_solicitacao = agora - timezone.timedelta(days=1)
    pendente.save()

    ctx["usuarios"] = criados
    ctx["diretor"] = marina
    ctx["diretores"] = [marina, criados["rafael.costa@usp.br"]]
    ctx["atletas"] = [a for a in criados.values() if a.situacao == "ativa"]
    ctx["ana"] = criados["ana.lima@usp.br"]
    ctx["bruno"] = criados["bruno.kato@usp.br"]
    ctx["carla"] = criados["carla.mendes@usp.br"]
    return f"{len(criados)} usuários (senha: {SENHA})"