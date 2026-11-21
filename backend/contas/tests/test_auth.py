"""Testes do login (UC01): códigos de resposta e mensagens do contrato da API."""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso

SENHA = "pingpoli123"


def criar(email, nusp, papel="atleta", situacao="ativa"):
    return get_user_model().objects.create_user(
        email, SENHA, nome=email.split("@")[0], nusp=nusp,
        curso=Curso.objects.first(), ano_ingresso=2024, papel=papel, situacao=situacao,
    )


class LoginTests(APITestCase):
    url = "/api/v1/auth/login/"

    def setUp(self):
        self.ana = criar("ana.lima@usp.br", 1)

    def login(self, email, senha):
        return self.client.post(self.url, {"email": email, "senha": senha}, format="json")

    def test_login_com_sucesso_devolve_token_e_dados(self):
        r = self.login("Ana.Lima@USP.br", SENHA)  # e-mail em maiúsculas também funciona
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["token"], Token.objects.get(user=self.ana).key)
        self.assertEqual(r.data["atleta"]["papel"], "atleta")
        self.ana.refresh_from_db()
        self.assertIsNotNone(self.ana.last_login)

    def test_campos_vazios(self):
        r = self.login("", "")
        self.assertEqual((r.status_code, r.data["codigo"]), (400, "campos_obrigatorios"))

    def test_email_invalido(self):
        r = self.login("ana-sem-arroba", SENHA)
        self.assertEqual((r.status_code, r.data["codigo"]), (400, "email_invalido"))

    def test_senha_errada_e_email_inexistente_tem_a_mesma_resposta(self):
        r1 = self.login("ana.lima@usp.br", "errada123")
        r2 = self.login("ninguem@usp.br", "errada123")
        self.assertEqual(r1.status_code, 401)
        self.assertEqual(r1.data, r2.data)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.tentativas_login, 1)

    def test_situacao_so_e_revelada_com_a_senha_certa(self):
        for n, (situacao, codigo) in enumerate(
            [("pendente", "conta_pendente"), ("recusada", "conta_recusada"), ("inativa", "conta_inativa")], start=10
        ):
            with self.subTest(situacao=situacao):
                criar(f"x{n}@usp.br", n, situacao=situacao)
                self.assertEqual(self.login(f"x{n}@usp.br", "errada123").data["codigo"], "credenciais_invalidas")
                r = self.login(f"x{n}@usp.br", SENHA)
                self.assertEqual((r.status_code, r.data["codigo"]), (403, codigo))


class MeLogoutTests(APITestCase):
    def setUp(self):
        self.marina = criar("marina.souza@usp.br", 2, papel="diretor")
        self.token = Token.objects.create(user=self.marina)

    def test_me_sem_token_da_401(self):
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    def test_me_com_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        r = self.client.get("/api/v1/auth/me/")
        self.assertEqual((r.status_code, r.data["email"], r.data["papel"]), (200, "marina.souza@usp.br", "diretor"))

    def test_logout_invalida_o_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.assertEqual(self.client.post("/api/v1/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    def test_cursos_e_publico(self):
        r = self.client.get("/api/v1/cursos/")
        self.assertEqual((r.status_code, len(r.data)), (200, 13))