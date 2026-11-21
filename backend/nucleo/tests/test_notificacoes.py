"""Testes das notificações (sino da barra de navegação)."""
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contas.models import Curso
from nucleo.servicos import notificar

Atleta = get_user_model()


def criar(email, nusp):
    return Atleta.objects.create_user(
        email, "pingpoli123", nome=email.split("@")[0].title(), nusp=nusp,
        curso=Curso.objects.first(), ano_ingresso=2024, situacao="ativa",
    )


class NotificacoesTests(APITestCase):
    def setUp(self):
        self.ana = criar("ana@usp.br", 1)
        self.bruno = criar("bruno@usp.br", 2)
        self.n1 = notificar(self.ana, "partida_pendente", "Bruno registrou uma partida", "/partidas/pendentes")
        self.n2 = notificar(self.ana, "aviso_novo", "Novo aviso urgente")
        self.do_bruno = notificar(self.bruno, "aviso_novo", "Novo aviso urgente")
        token = Token.objects.create(user=self.ana)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_lista_so_as_proprias_mais_recentes_primeiro(self):
        r = self.client.get("/api/v1/notificacoes/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([n["id"] for n in r.data], [self.n2.id, self.n1.id])
        self.assertEqual(set(r.data[0]), {"id", "tipo", "mensagem", "link", "lida", "data_criacao"})

    def test_marcar_uma_como_lida(self):
        r = self.client.post(f"/api/v1/notificacoes/{self.n1.id}/lida/")
        self.assertEqual((r.status_code, r.data["lida"]), (200, True))
        r = self.client.get("/api/v1/notificacoes/", {"nao_lidas": "1"})
        self.assertEqual([n["id"] for n in r.data], [self.n2.id])

    def test_nao_marca_notificacao_de_outra_pessoa(self):
        r = self.client.post(f"/api/v1/notificacoes/{self.do_bruno.id}/lida/")
        self.assertEqual(r.status_code, 404)
        self.do_bruno.refresh_from_db()
        self.assertFalse(self.do_bruno.lida)

    def test_marcar_todas(self):
        r = self.client.post("/api/v1/notificacoes/marcar-todas/")
        self.assertEqual((r.status_code, r.data["marcadas"]), (200, 2))
        self.assertEqual(self.client.get("/api/v1/notificacoes/", {"nao_lidas": "1"}).data, [])
        self.do_bruno.refresh_from_db()
        self.assertFalse(self.do_bruno.lida)

    def test_sem_login(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/notificacoes/").status_code, 401)