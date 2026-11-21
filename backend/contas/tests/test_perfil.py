"""Testes de Meu Perfil e troca de senha (UC04)."""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso

Atleta = get_user_model()


class PerfilTests(APITestCase):
    def setUp(self):
        self.ana = Atleta.objects.create_user(
            "ana@usp.br", "pingpoli123", nome="Ana Lima", nusp=1, curso=Curso.objects.first(),
            ano_ingresso=2024, situacao="ativa",
        )
        token = Token.objects.create(user=self.ana)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_ver_perfil(self):
        r = self.client.get("/api/v1/perfil/")
        self.assertEqual((r.status_code, r.data["email"], r.data["curso"]["id"]), (200, "ana@usp.br", self.ana.curso_id))

    def test_editar_perfil(self):
        outro_curso = Curso.objects.last()
        r = self.client.patch("/api/v1/perfil/", {
            "nome": "Ana  Paula Lima", "telefone": "(11) 91234-5678", "curso": outro_curso.id, "mao_dominante": "canhoto",
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data["nome"], r.data["curso"]["nome"]), ("Ana Paula Lima", outro_curso.nome))

    def test_email_e_nusp_nao_mudam(self):
        self.client.patch("/api/v1/perfil/", {"email": "outro@usp.br", "nusp": 999}, format="json")
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.email, self.ana.nusp), ("ana@usp.br", 1))

    def test_validacoes(self):
        r = self.client.patch("/api/v1/perfil/", {"telefone": "123", "ano_ingresso": 1990}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {"telefone", "ano_ingresso"})

    def test_trocar_senha(self):
        r = self.client.post("/api/v1/perfil/senha/", {
            "senha_atual": "pingpoli123", "nova_senha": "novasenha99", "confirmacao": "novasenha99"}, format="json")
        self.assertEqual(r.status_code, 204)
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password("novasenha99"))

    def test_trocar_senha_erros(self):
        r = self.client.post("/api/v1/perfil/senha/", {
            "senha_atual": "errada", "nova_senha": "curta", "confirmacao": "outra"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("senha_atual", r.data)
        self.assertIn("nova_senha", r.data)

    def test_confirmacao_diferente(self):
        r = self.client.post("/api/v1/perfil/senha/", {
            "senha_atual": "pingpoli123", "nova_senha": "novasenha99", "confirmacao": "novasenha00"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("confirmacao", r.data)

    def test_sem_login(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/perfil/").status_code, 401)