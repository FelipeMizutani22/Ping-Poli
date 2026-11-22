"""Testes da API de adversários externos (UC15-a e UC15-j)."""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso
from partidas.models import AdversarioExterno

URL = "/api/v1/adversarios-externos/"


class AdversarioExternoTests(APITestCase):
    def setUp(self):
        self.ana = get_user_model().objects.create_user(
            "ana@usp.br", "pingpoli123", nome="Ana Lima", nusp=1001,
            curso=Curso.objects.first(), ano_ingresso=2024, situacao="ativa",
        )
        token, _ = Token.objects.get_or_create(user=self.ana)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.carlos = AdversarioExterno.objects.create(nome="Carlos Pereira", clube="ECP")
        AdversarioExterno.objects.create(nome="Marta Souza", clube="")

    def test_cadastra_adversario(self):
        r = self.client.post(URL, {"nome": "  Jorge Lima ", "clube": "Pinheiros"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["nome"], "Jorge Lima")
        self.assertEqual(r.data["clube"], "Pinheiros")
        self.assertTrue(AdversarioExterno.objects.filter(nome="Jorge Lima").exists())

    def test_clube_e_opcional(self):
        r = self.client.post(URL, {"nome": "Paulo Reis"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["clube"], "")

    def test_duplicado_e_recusado_sem_diferenciar_maiusculas(self):
        r = self.client.post(URL, {"nome": "carlos PEREIRA", "clube": "Outro"}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["codigo"], "ja_existe")
        self.assertEqual(r.data["detail"], "Adversário externo já cadastrado")
        self.assertEqual(r.data["existente"], {"id": self.carlos.id, "nome": "Carlos Pereira", "clube": "ECP"})
        self.assertEqual(AdversarioExterno.objects.count(), 2)

    def test_nome_com_menos_de_3_caracteres(self):
        r = self.client.post(URL, {"nome": "Jo"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("nome", r.data)

    def test_nome_obrigatorio(self):
        r = self.client.post(URL, {"clube": "ECP"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("nome", r.data)

    def test_busca_por_nome(self):
        r = self.client.get(URL, {"q": "carl"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, [{"id": self.carlos.id, "nome": "Carlos Pereira", "clube": "ECP", "partidas": 0}])

    def test_lista_tudo_em_ordem_alfabetica_sem_busca(self):
        r = self.client.get(URL)
        self.assertEqual([a["nome"] for a in r.data], ["Carlos Pereira", "Marta Souza"])

    def test_sem_login_da_401(self):
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)
