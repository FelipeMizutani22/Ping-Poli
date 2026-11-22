"""Testes da moderação de partidas pelo Diretor (UC17 · B7)."""
from nucleo.models import Notificacao
from partidas.models import HistoricoPartida, Partida
from partidas.tests.test_partidas_api import S, BasePartidas, criar_atleta

PROPOSTO = [S(11, 7), S(9, 11), S(9, 11), S(11, 8), S(9, 11)]   # Bruno vence 3–2


class ModeracaoTests(BasePartidas):
    def setUp(self):
        super().setUp()
        self.partida_id = self.registrar().data["id"]   # Ana × Bruno, 3–1 para a Ana
        self.entrar(self.bruno)
        self.client.post(f"/api/v1/partidas/{self.partida_id}/contestar/",
                         {"justificativa": "Os dois últimos sets foram meus.", "sets": PROPOSTO}, format="json")
        Notificacao.objects.all().delete()
        self.entrar(self.marina)

    def moderar(self, decisao, motivo="Conferi com a súmula do jogo.", **extra):
        return self.client.post(f"/api/v1/partidas/{self.partida_id}/moderar/",
                                {"decisao": decisao, "motivo": motivo, **extra}, format="json")

    def partida(self):
        return Partida.objects.get(pk=self.partida_id)

    def test_manter_placar_registrado(self):
        r = self.moderar("manter")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "confirmada")
        self.assertEqual(r.data["placar_sets"], {"atleta": 3, "adversario": 1})
        self.assertEqual(r.data["contestacao"]["resolvida_por"]["id"], self.marina.id)
        self.assertEqual(r.data["contestacao"]["motivo_decisao"], "Conferi com a súmula do jogo.")

    def test_aceitar_placar_proposto(self):
        r = self.moderar("aceitar_proposto")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["placar_sets"], {"atleta": 2, "adversario": 3})
        self.assertEqual(r.data["vencedor"], "adversario")

    def test_editar_com_as_regras_do_uc15(self):
        dados = self.dados(formato=3, sets=[S(11, 9), S(11, 9)])
        r = self.moderar("editar", dados=dados)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data["formato"], len(r.data["sets"])), (3, 2))

    def test_editar_com_placar_invalido(self):
        r = self.moderar("editar", dados=self.dados(sets=[S(11, 10)]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("sets", r.data["dados"])
        self.assertEqual(self.partida().status, "contestada")

    def test_remover(self):
        r = self.moderar("remover")
        self.assertEqual(r.data["status"], "removida")
        self.assertEqual(Notificacao.objects.filter(tipo="partida_removida").count(), 2)

    def test_historico_gravado_antes_de_alterar(self):
        self.moderar("aceitar_proposto")
        h = HistoricoPartida.objects.get(partida_id=self.partida_id)
        self.assertEqual(h.alterado_por, self.marina)
        r = self.client.get(f"/api/v1/partidas/{self.partida_id}/historico/")
        self.assertEqual(r.status_code, 200)
        anterior = r.data[0]["valores_anteriores"]
        self.assertEqual(anterior["status"], "contestada")
        self.assertEqual(anterior["placar_sets"], {"atleta": 3, "adversario": 1})

    def test_notifica_os_dois_jogadores(self):
        self.moderar("manter")
        destinatarios = set(Notificacao.objects.filter(tipo="partida_moderada").values_list("destinatario", flat=True))
        self.assertEqual(destinatarios, {self.ana.id, self.bruno.id})

    def test_motivo_curto(self):
        r = self.moderar("manter", motivo="ok")
        self.assertEqual(r.status_code, 400)
        self.assertIn("motivo", r.data)

    def test_atleta_nao_modera(self):
        self.entrar(self.carla)
        self.assertEqual(self.moderar("manter").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/partidas/{self.partida_id}/historico/").status_code, 403)

    def test_manter_so_vale_para_contestada(self):
        self.moderar("manter")
        r = self.moderar("manter")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["codigo"], "situacao_invalida")

    def test_conflito_de_interesse_com_outro_diretor_ativo(self):
        criar_atleta("paulo@usp.br", "Paulo Diretor", 1009, papel="diretor")
        Partida.objects.filter(pk=self.partida_id).update(atleta=self.marina)
        r = self.moderar("manter")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["codigo"], "conflito_interesse")

    def test_unico_diretor_jogador_pode_moderar_e_fica_marcado(self):
        Partida.objects.filter(pk=self.partida_id).update(atleta=self.marina)
        r = self.moderar("manter")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(HistoricoPartida.objects.get().motivo.startswith("[moderada pelo próprio jogador]"))
