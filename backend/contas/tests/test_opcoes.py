"""Testes da busca de atletas (atletas/opcoes/), usada pelas telas de partida, presença e confronto."""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso

URL = "/api/v1/atletas/opcoes/"


def criar(email, nome, nusp, situacao="ativa"):
    return get_user_model().objects.create_user(
        email, "pingpoli123", nome=nome, nusp=nusp, curso=Curso.objects.first(),
        ano_ingresso=2024, situacao=situacao,
    )


class AtletaOpcoesTests(APITestCase):
    def setUp(self):
        self.ana = criar("ana@usp.br", "Ana Lima", 1001)
        self.bruno = criar("bruno@usp.br", "Bruno Kato", 1002)
        self.anabela = criar("anabela@usp.br", "Anabela Reis", 1003)
        criar("igor@usp.br", "Igor Pereira", 1004, situacao="inativa")
        criar("julia@usp.br", "Júlia Martins", 1005, situacao="pendente")
        self.entrar(self.bruno)

    def entrar(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def nomes(self, **params):
        r = self.client.get(URL, params)
        self.assertEqual(r.status_code, 200)
        return [a["nome"] for a in r.data]

    def test_busca_por_nome_sem_diferenciar_maiusculas(self):
        self.assertEqual(self.nomes(q="ANA"), ["Ana Lima", "Anabela Reis"])

    def test_busca_por_nusp(self):
        self.assertEqual(self.nomes(q="1001"), ["Ana Lima"])

    def test_resposta_tem_formato_resumido(self):
        r = self.client.get(URL, {"q": "Ana Lima"})
        self.assertEqual(r.data, [{"id": self.ana.id, "nome": "Ana Lima", "nusp": 1001}])

    def test_nao_inclui_o_proprio_usuario_nem_contas_nao_ativas(self):
        self.assertEqual(self.nomes(), ["Ana Lima", "Anabela Reis"])

    def test_inativos_so_com_parametro(self):
        self.assertIn("Igor Pereira", self.nomes(incluir_inativos="1"))
        self.assertNotIn("Júlia Martins", self.nomes(incluir_inativos="1"))

    def test_limite_de_20_resultados(self):
        for i in range(25):
            criar(f"extra{i}@usp.br", f"Extra {i:02d}", 2000 + i)
        self.assertEqual(len(self.nomes()), 20)

    def test_sem_login_da_401(self):
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_conta_pendente_com_token_da_403(self):
        julia = get_user_model().objects.get(email="julia@usp.br")
        self.entrar(julia)
        self.assertEqual(self.client.get(URL).status_code, 403)