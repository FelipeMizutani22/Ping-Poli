"""Testes do ajuste de presenças pelo Diretor (UC10 · C9): sem janela, com justificativa e auditoria."""
from datetime import time, timedelta

from calendario.models import Presenca
from calendario.tests.test_calendario_api import HOJE, BaseCalendario
from nucleo.models import Auditoria
from partidas.tests.test_partidas_api import criar_atleta


class AjustePresencasTests(BaseCalendario):
    def setUp(self):
        super().setUp()
        self.carla = criar_atleta("carla@usp.br", "Carla Dias", 1003)
        self.treino = self.evento(dias=-3)   # já ocorreu
        Presenca.objects.create(evento=self.treino, atleta=self.ana, registrado_por=self.ana)
        Presenca.objects.create(evento=self.treino, atleta=self.bruno, registrado_por=self.ana)
        self.url = f"/api/v1/eventos/{self.treino.id}/ajuste/"   # logado como Marina (Diretora)

    def presentes(self):
        return set(Presenca.objects.filter(evento=self.treino).values_list("atleta_id", flat=True))

    def test_get_lista_os_atletas_ativos_com_a_presenca(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["ajustavel"])
        linhas = {l["atleta"]["nome"]: l for l in r.data["atletas"]}
        self.assertEqual(set(linhas), {"Ana Lima", "Bruno Kato", "Carla Dias", "Marina Diretora"})
        self.assertTrue(linhas["Bruno Kato"]["presente"])
        self.assertEqual(linhas["Bruno Kato"]["registrado_por"]["id"], self.ana.id)
        self.assertFalse(linhas["Carla Dias"]["presente"])
        self.assertIsNone(linhas["Carla Dias"]["registrado_por"])

    def test_incluir_sem_justificativa(self):
        r = self.client.put(self.url, {"presentes": [self.ana.id, self.bruno.id, self.carla.id]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data, {"incluidos": [self.carla.id], "removidos": []})
        self.assertEqual(Presenca.objects.get(atleta=self.carla).registrado_por, self.marina)
        log = Auditoria.objects.get()
        self.assertEqual((log.entidade, log.acao, log.autor), ("presenca", "incluir", self.marina))

    def test_remover_exige_justificativa(self):
        r = self.client.put(self.url, {"presentes": [self.ana.id]}, format="json")
        self.assertEqual((r.status_code, r.data["codigo"]), (400, "justificativa_obrigatoria"))
        self.assertEqual(self.presentes(), {self.ana.id, self.bruno.id})
        r = self.client.put(self.url, {"presentes": [self.ana.id], "justificativa": "ok"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("justificativa", r.data)

    def test_incluir_e_remover_audita_cada_mudanca(self):
        r = self.client.put(self.url, {"presentes": [self.ana.id, self.carla.id],
                                       "justificativa": "Bruno saiu antes do aquecimento"}, format="json")
        self.assertEqual(r.data, {"incluidos": [self.carla.id], "removidos": [self.bruno.id]})
        self.assertEqual(self.presentes(), {self.ana.id, self.carla.id})
        acoes = sorted(Auditoria.objects.values_list("acao", flat=True))
        self.assertEqual(acoes, ["incluir", "remover"])
        self.assertTrue(all(a.justificativa == "Bruno saiu antes do aquecimento" for a in Auditoria.objects.all()))

    def test_sem_mudanca_nao_audita(self):
        r = self.client.put(self.url, {"presentes": [self.bruno.id, self.ana.id]}, format="json")
        self.assertEqual(r.data, {"incluidos": [], "removidos": []})
        self.assertFalse(Auditoria.objects.exists())

    def test_treino_futuro_cancelado_ou_atividade_nao_ajusta(self):
        futuro = self.evento(dias=2)
        cancelado = self.evento(dias=-1, status="cancelado")
        atividade = self.evento(dias=-1, tipo="atividade")
        for evento in (futuro, cancelado, atividade):
            r = self.client.get(f"/api/v1/eventos/{evento.id}/ajuste/")
            self.assertFalse(r.data["ajustavel"])
            self.assertEqual(r.data["mensagem"], "Só é possível ajustar presenças de treinos Agendados que já ocorreram")
            r = self.client.put(f"/api/v1/eventos/{evento.id}/ajuste/", {"presentes": [self.ana.id]}, format="json")
            self.assertEqual((r.status_code, r.data["codigo"]), (409, "treino_nao_ajustavel"))

    def test_treino_de_hoje_que_ainda_nao_terminou(self):
        treino = self.evento(dias=0, hora_inicio=time(0, 0), hora_fim=time(23, 59))
        self.assertFalse(self.client.get(f"/api/v1/eventos/{treino.id}/ajuste/").data["ajustavel"])

    def test_atleta_inativo_so_se_ja_estava_presente(self):
        self.bruno.situacao = "inativa"
        self.bruno.save()
        ivo = criar_atleta("ivo@usp.br", "Ivo Inativo", 1009, situacao="inativa")
        ok = self.client.put(self.url, {"presentes": [self.ana.id, self.bruno.id]}, format="json")
        self.assertEqual(ok.status_code, 200)
        r = self.client.put(self.url, {"presentes": [self.ana.id, self.bruno.id, ivo.id]}, format="json")
        self.assertEqual((r.status_code, r.data["codigo"]), (400, "atleta_invalido"))

    def test_so_diretor(self):
        self.entrar(self.ana)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.put(self.url, {"presentes": []}, format="json").status_code, 403)

    def test_calendario_traz_total_de_presentes(self):
        inicio = (HOJE() - timedelta(days=5)).isoformat()
        r = self.client.get("/api/v1/calendario/", {"inicio": inicio, "fim": HOJE().isoformat(), "tipo": "treino"})
        self.assertEqual(r.data[0]["total_presentes"], 2)
