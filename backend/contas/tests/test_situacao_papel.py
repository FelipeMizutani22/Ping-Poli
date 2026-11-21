"""Testes de inativar, reativar e mudar o perfil (UC03)."""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso
from nucleo.models import Auditoria

Atleta = get_user_model()


def criar(email, nusp, papel="atleta", situacao="ativa"):
    return Atleta.objects.create_user(
        email, "pingpoli123", nome=email.split("@")[0].title(), nusp=nusp,
        curso=Curso.objects.first(), ano_ingresso=2024, papel=papel, situacao=situacao,
    )


class SituacaoPapelTests(APITestCase):
    def setUp(self):
        self.marina = criar("marina@usp.br", 1, papel="diretor")
        self.ana = criar("ana@usp.br", 2)
        self.entrar(self.marina)

    def entrar(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def post(self, atleta, acao, dados=None):
        return self.client.post(f"/api/v1/atletas/{atleta.id}/{acao}/", dados or {}, format="json")

    def test_inativar_encerra_a_sessao_e_audita(self):
        Token.objects.create(user=self.ana)
        r = self.post(self.ana, "inativar", {"justificativa": "Saiu da equipe"})
        self.assertEqual((r.status_code, r.data["situacao"]), (200, "inativa"))
        self.assertFalse(Token.objects.filter(user=self.ana).exists())
        self.assertTrue(Auditoria.objects.filter(registro_id=self.ana.id, acao="inativar").exists())

    def test_reativar(self):
        self.post(self.ana, "inativar")
        r = self.post(self.ana, "reativar")
        self.assertEqual((r.status_code, r.data["situacao"]), (200, "ativa"))

    def test_transicao_invalida(self):
        r = self.post(self.ana, "reativar")  # já está ativa
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "situacao_invalida"))
        pendente = criar("julia@usp.br", 3, situacao="pendente")
        self.assertEqual(self.post(pendente, "inativar").status_code, 409)

    def test_promover_e_rebaixar(self):
        r = self.post(self.ana, "papel", {"papel": "diretor"})
        self.assertEqual((r.status_code, r.data["papel"]), (200, "diretor"))
        r = self.post(self.ana, "papel", {"papel": "atleta"})  # Marina continua diretora
        self.assertEqual((r.status_code, r.data["papel"]), (200, "atleta"))

    def test_protege_o_ultimo_diretor(self):
        r = self.post(self.marina, "papel", {"papel": "atleta"})
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "ultimo_diretor"))
        r = self.post(self.marina, "inativar")
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "ultimo_diretor"))

    def test_com_dois_diretores_um_pode_sair(self):
        self.post(self.ana, "papel", {"papel": "diretor"})
        self.assertEqual(self.post(self.marina, "papel", {"papel": "atleta"}).status_code, 200)

    def test_papel_invalido(self):
        r = self.post(self.ana, "papel", {"papel": "rei"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("papel", r.data)

    def test_atleta_comum_nao_acessa(self):
        self.entrar(self.ana)
        self.assertEqual(self.post(self.marina, "inativar").status_code, 403)   