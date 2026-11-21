"""Testes da gestão de atletas pelo Diretor (UC03): lista, aprovar e recusar."""
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso
from nucleo.models import Auditoria, Notificacao

Atleta = get_user_model()


def criar(email, nome, nusp, papel="atleta", situacao="ativa"):
    return Atleta.objects.create_user(
        email, "pingpoli123", nome=nome, nusp=nusp, curso=Curso.objects.first(),
        ano_ingresso=2024, papel=papel, situacao=situacao,
    )


class GestaoAtletasTests(APITestCase):
    def setUp(self):
        self.marina = criar("marina@usp.br", "Marina Souza", 1, papel="diretor")
        self.ana = criar("ana@usp.br", "Ana Lima", 2)
        self.julia = criar("julia@usp.br", "Júlia Martins", 3, situacao="pendente")
        self.entrar(self.marina)

    def entrar(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_atleta_comum_nao_acessa(self):
        self.entrar(self.ana)
        self.assertEqual(self.client.get("/api/v1/atletas/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/atletas/{self.julia.id}/aprovar/").status_code, 403)

    def test_lista_paginada_com_filtros(self):
        r = self.client.get("/api/v1/atletas/", {"situacao": "pendente"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(r.data["results"][0]["email"], "julia@usp.br")
        r = self.client.get("/api/v1/atletas/", {"busca": "ana"})
        self.assertEqual([a["nome"] for a in r.data["results"]], ["Ana Lima"])

    def test_pagina_tem_20_itens(self):
        for i in range(25):
            criar(f"x{i}@usp.br", f"Extra {i:02d}", 100 + i)
        r = self.client.get("/api/v1/atletas/")
        self.assertEqual((r.data["count"], len(r.data["results"])), (28, 20))
        self.assertIsNotNone(r.data["next"])

    def test_aprovar(self):
        r = self.client.post(f"/api/v1/atletas/{self.julia.id}/aprovar/")
        self.assertEqual((r.status_code, r.data["situacao"]), (200, "ativa"))
        self.julia.refresh_from_db()
        self.assertEqual(self.julia.avaliado_por, self.marina)
        self.assertIsNotNone(self.julia.data_avaliacao)
        self.assertTrue(Notificacao.objects.filter(destinatario=self.julia, tipo="cadastro_aprovado").exists())
        self.assertEqual(mail.outbox[0].to, ["julia@usp.br"])
        self.assertTrue(Auditoria.objects.filter(entidade="atleta", registro_id=self.julia.id, acao="aprovar").exists())
        # e agora ela consegue logar
        r = self.client.post("/api/v1/auth/login/", {"email": "julia@usp.br", "senha": "pingpoli123"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_recusar_exige_motivo(self):
        r = self.client.post(f"/api/v1/atletas/{self.julia.id}/recusar/", {"motivo": ""}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("motivo", r.data)

    def test_recusar(self):
        r = self.client.post(f"/api/v1/atletas/{self.julia.id}/recusar/", {"motivo": "Não é aluna da Poli"}, format="json")
        self.assertEqual((r.status_code, r.data["situacao"], r.data["motivo_recusa"]), (200, "recusada", "Não é aluna da Poli"))

    def test_so_aprova_ou_recusa_pendente(self):
        r = self.client.post(f"/api/v1/atletas/{self.ana.id}/aprovar/")
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "situacao_invalida"))

    def test_atleta_inexistente_da_404(self):
        self.assertEqual(self.client.post("/api/v1/atletas/9999/aprovar/").status_code, 404)