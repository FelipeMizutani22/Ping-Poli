from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from contas.models import Curso
from contas.permissoes import AtletaAtivo, Diretor


def criar(email, nusp, papel="atleta", situacao="ativa"):
    return get_user_model().objects.create_user(
        email, "pingpoli123", nome=email.split("@")[0], nusp=nusp,
        curso=Curso.objects.first(), ano_ingresso=2024, papel=papel, situacao=situacao,
    )


def pode(permissao, usuario):
    return permissao().has_permission(SimpleNamespace(user=usuario), None)


class PermissoesTests(TestCase):
    def test_atleta_ativo(self):
        ana = criar("ana@usp.br", 1)
        self.assertTrue(pode(AtletaAtivo, ana))
        self.assertFalse(pode(Diretor, ana))

    def test_diretor_ativo(self):
        marina = criar("marina@usp.br", 2, papel="diretor")
        self.assertTrue(pode(AtletaAtivo, marina))
        self.assertTrue(pode(Diretor, marina))

    def test_contas_nao_ativas_e_anonimo_sao_barrados(self):
        for n, situacao in enumerate(["pendente", "recusada", "inativa"], start=10):
            with self.subTest(situacao=situacao):
                self.assertFalse(pode(AtletaAtivo, criar(f"x{n}@usp.br", n, situacao=situacao)))
        self.assertFalse(pode(AtletaAtivo, AnonymousUser()))

    def test_diretor_inativo_perde_acesso(self):
        self.assertFalse(pode(Diretor, criar("rafael@usp.br", 3, papel="diretor", situacao="inativa")))