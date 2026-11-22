"""Testes de confirmar e contestar partida (UC16 · B5)."""
from nucleo.models import Notificacao
from partidas.models import Contestacao, Partida
from partidas.tests.test_partidas_api import S, BasePartidas


class ConfirmarContestarTests(BasePartidas):
    def setUp(self):
        super().setUp()
        self.partida_id = self.registrar().data["id"]   # Ana registra contra o Bruno → pendente
        Notificacao.objects.all().delete()
        self.entrar(self.bruno)

    def url(self, acao):
        return f"/api/v1/partidas/{self.partida_id}/{acao}/"

    # --- confirmar ---
    def test_adversario_confirma(self):
        r = self.client.post(self.url("confirmar"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "confirmada")
        self.assertIsNotNone(r.data["data_confirmacao"])
        self.assertEqual(Notificacao.objects.get(destinatario=self.ana).tipo, "partida_confirmada")

    def test_so_o_adversario_pode_confirmar(self):
        for quem in (self.ana, self.carla, self.marina):
            with self.subTest(quem=quem.nome):
                self.entrar(quem)
                r = self.client.post(self.url("confirmar"))
                self.assertEqual(r.status_code, 403)
        self.assertEqual(Partida.objects.get(pk=self.partida_id).status, "pendente")

    def test_confirmar_duas_vezes_da_409(self):
        self.client.post(self.url("confirmar"))
        r = self.client.post(self.url("confirmar"))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["codigo"], "nao_pendente")
        self.assertEqual(r.data["status"], "confirmada")

    def test_partida_inexistente_da_404(self):
        self.assertEqual(self.client.post("/api/v1/partidas/9999/confirmar/").status_code, 404)

    # --- contestar ---
    def test_contestar_com_placar_proposto(self):
        r = self.client.post(self.url("contestar"), {
            "justificativa": "O terceiro set foi meu, 11 a 9.",
            "sets": [S(11, 7), S(9, 11), S(9, 11), S(11, 8), S(9, 11)],
        }, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "contestada")
        c = r.data["contestacao"]
        self.assertEqual(c["contestante"]["id"], self.bruno.id)
        self.assertEqual(len(c["sets_propostos"]), 5)
        self.assertEqual(len(r.data["sets"]), 4)   # o placar oficial continua o registrado
        self.assertTrue(Notificacao.objects.filter(destinatario=self.ana, tipo="partida_contestada").exists())
        self.assertTrue(Notificacao.objects.filter(destinatario=self.marina, tipo="partida_contestada").exists())

    def test_contestar_sem_placar_proposto(self):
        r = self.client.post(self.url("contestar"), {"justificativa": "Essa partida não aconteceu."}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["contestacao"]["sets_propostos"], [])

    def test_justificativa_curta(self):
        r = self.client.post(self.url("contestar"), {"justificativa": "errado"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("justificativa", r.data)
        self.assertFalse(Contestacao.objects.exists())

    def test_placar_proposto_invalido(self):
        r = self.client.post(self.url("contestar"), {
            "justificativa": "O placar certo é outro.", "sets": [S(11, 10), S(11, 5), S(11, 3)],
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["sets"], ["Set 1: o vencedor precisa de 11 pontos com 2 de vantagem"])

    def test_nao_contesta_partida_ja_confirmada(self):
        self.client.post(self.url("confirmar"))
        r = self.client.post(self.url("contestar"), {"justificativa": "Mudei de ideia sobre isso."}, format="json")
        self.assertEqual(r.status_code, 409)

    def test_contestada_aparece_para_o_diretor(self):
        self.client.post(self.url("contestar"), {"justificativa": "Essa partida não aconteceu."}, format="json")
        self.entrar(self.marina)
        r = self.client.get("/api/v1/partidas/", {"escopo": "contestadas"})
        self.assertEqual([p["id"] for p in r.data], [self.partida_id])
