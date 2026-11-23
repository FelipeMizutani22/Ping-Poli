"""Testes da edição dos dados de um membro pelo Diretor (UC03-b)."""
import json

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso
from nucleo.models import Auditoria

Atleta = get_user_model()


def criar(email, nusp, papel="atleta"):
    return Atleta.objects.create_user(
        email, "pingpoli123", nome=email.split("@")[0].title(), nusp=nusp,
        curso=Curso.objects.first(), ano_ingresso=2020, papel=papel, situacao="ativa",
    )


class EdicaoAtletaTests(APITestCase):
    def setUp(self):
        self.marina = criar("marina@usp.br", 1, papel="diretor")
        self.ana = criar("ana@usp.br", 2)
        self.entrar(self.marina)
        self.url = f"/api/v1/atletas/{self.ana.id}/"

    def entrar(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_diretor_troca_o_email_de_um_formado(self):
        r = self.client.patch(self.url, {"email": "Ana.Lima@Gmail.com", "ano_ingresso": 2012}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data["email"], r.data["ano_ingresso"]), ("ana.lima@gmail.com", 2012))
        auditoria = Auditoria.objects.get(registro_id=self.ana.id, acao="editar")
        self.assertEqual(json.loads(auditoria.valor_anterior)["email"], "ana@usp.br")
        self.assertEqual(mail.outbox[0].to, ["ana.lima@gmail.com"])
        # e ela entra com o e-mail novo
        self.client.credentials()
        r = self.client.post("/api/v1/auth/login/", {"email": "ana.lima@gmail.com", "senha": "pingpoli123"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_email_repetido(self):
        r = self.client.patch(self.url, {"email": "marina@usp.br"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.data)

    def test_nusp_nao_muda(self):
        self.client.patch(self.url, {"nusp": 999, "nome": "Ana Paula Lima"}, format="json")
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.nusp, self.ana.nome), (2, "Ana Paula Lima"))

    def test_sem_mudanca_nao_audita(self):
        self.client.patch(self.url, {"nome": self.ana.nome}, format="json")
        self.assertFalse(Auditoria.objects.filter(acao="editar").exists())

    def test_atleta_comum_nao_edita(self):
        self.entrar(self.ana)
        self.assertEqual(self.client.patch(f"/api/v1/atletas/{self.marina.id}/", {"nome": "X"}, format="json").status_code, 403)
