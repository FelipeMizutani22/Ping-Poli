"""Testes do relatório de frequência (UC11 · C10)."""
from datetime import time, timedelta

from calendario.models import Presenca
from calendario.tests.test_calendario_api import HOJE, BaseCalendario
from partidas.tests.test_partidas_api import criar_atleta

URL = "/api/v1/frequencia/"


class FrequenciaTests(BaseCalendario):
    def setUp(self):
        super().setUp()
        self.carla = criar_atleta("carla@usp.br", "Carla Dias", 1003)
        # período fixo de 30 dias para trás: três treinos realizados, um cancelado, um futuro e uma atividade
        self.t1 = self.evento(dias=-10)
        self.t2 = self.evento(dias=-5)
        self.t3 = self.evento(dias=-2)
        self.evento(dias=-3, status="cancelado")
        self.evento(dias=-4, tipo="atividade")
        self.futuro = self.evento(dias=3)
        for t in (self.t1, self.t2):
            Presenca.objects.create(evento=t, atleta=self.ana, registrado_por=self.ana)
        Presenca.objects.create(evento=self.t3, atleta=self.bruno, registrado_por=self.ana)
        self.periodo = {"inicio": (HOJE() - timedelta(days=30)).isoformat(), "fim": (HOJE() + timedelta(days=5)).isoformat()}

    def test_relatorio_individual(self):
        self.entrar(self.ana)
        r = self.client.get(URL, self.periodo)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["atleta"]["id"], self.ana.id)
        self.assertEqual([t["id"] for t in r.data["treinos"]], [self.t1.id, self.t2.id, self.t3.id])
        self.assertEqual((r.data["total_treinos"], r.data["presencas"], r.data["percentual"]), (3, 2, 66.7))
        self.assertTrue(r.data["treinos"][0]["presente"])
        self.assertEqual(r.data["treinos"][0]["registrado_por"]["id"], self.ana.id)
        self.assertFalse(r.data["treinos"][2]["presente"])
        self.assertIsNone(r.data["treinos"][2]["registrado_por"])

    def test_sem_treinos_nao_calcula_percentual(self):
        self.entrar(self.ana)
        r = self.client.get(URL, {"mes": "2020-01"})
        self.assertEqual((r.data["total_treinos"], r.data["percentual"]), (0, None))

    def test_mes_padrao_e_formato_do_mes(self):
        self.entrar(self.ana)
        r = self.client.get(URL)
        self.assertEqual(r.data["inicio"], HOJE().replace(day=1).isoformat())
        self.assertEqual(self.client.get(URL, {"mes": "nov/2026"}).status_code, 400)

    def test_periodo_invalido(self):
        self.entrar(self.ana)
        r = self.client.get(URL, {"inicio": "2026-11-10", "fim": "2026-11-01"})
        self.assertEqual(r.data, {"fim": ["A data final deve ser igual ou posterior à inicial"]})
        r = self.client.get(URL, {"inicio": "2025-01-01", "fim": "2026-01-01"})
        self.assertEqual(r.data, {"fim": ["O período não pode ultrapassar 12 meses"]})
        self.assertEqual(self.client.get(URL, {"inicio": "2026-01-01", "fim": "2026-12-31"}).status_code, 200)

    def test_atleta_nao_ve_a_de_outro(self):
        self.entrar(self.ana)
        self.assertEqual(self.client.get(URL, {"atleta": self.bruno.id}).status_code, 403)
        self.assertEqual(self.client.get(URL, {"atleta": self.ana.id}).status_code, 200)

    def test_diretor_ve_qualquer_atleta(self):
        r = self.client.get(URL, {**self.periodo, "atleta": self.bruno.id})
        self.assertEqual((r.data["atleta"]["id"], r.data["presencas"]), (self.bruno.id, 1))

    def test_matriz_da_equipe(self):
        r = self.client.get(f"{URL}equipe/", self.periodo)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([t["id"] for t in r.data["treinos"]], [self.t1.id, self.t2.id, self.t3.id])
        linhas = {l["atleta"]["nome"]: l for l in r.data["atletas"]}
        self.assertEqual(set(linhas), {"Ana Lima", "Bruno Kato", "Carla Dias", "Marina Diretora"})
        self.assertEqual(linhas["Ana Lima"]["presencas"], sorted([self.t1.id, self.t2.id]))
        self.assertEqual((linhas["Bruno Kato"]["total"], linhas["Bruno Kato"]["percentual"]), (1, 33.3))
        self.assertEqual(linhas["Carla Dias"]["percentual"], 0.0)
        self.assertIn("nome", linhas["Ana Lima"]["curso"])

    def test_inativo_fica_fora_da_matriz(self):
        criar_atleta("ivo@usp.br", "Ivo Inativo", 1009, situacao="inativa")
        nomes = [l["atleta"]["nome"] for l in self.client.get(f"{URL}equipe/", self.periodo).data["atletas"]]
        self.assertNotIn("Ivo Inativo", nomes)

    def test_equipe_so_para_diretor(self):
        self.entrar(self.ana)
        self.assertEqual(self.client.get(f"{URL}equipe/").status_code, 403)

    def test_treino_de_hoje_so_conta_depois_de_terminar(self):
        self.evento(dias=0, hora_inicio=time(0, 0), hora_fim=time(23, 59))
        self.entrar(self.ana)
        r = self.client.get(URL, self.periodo)
        self.assertEqual(r.data["total_treinos"], 3)
