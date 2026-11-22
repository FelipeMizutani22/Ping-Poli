"""Testes da presença no treino (UC09 · C8): janela, autor do registro e relação n×n atleta × evento."""
from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.utils import timezone

from calendario.models import Evento, Presenca
from calendario.regras import dentro_da_janela, janela
from calendario.tests.test_calendario_api import HOJE, BaseCalendario
from nucleo.models import Notificacao
from partidas.tests.test_partidas_api import criar_atleta


def as_(hora, minuto=0):
    """Um momento de HOJE no fuso do servidor, para fixar o relógio da janela."""
    return datetime.combine(HOJE(), time(hora, minuto), tzinfo=timezone.get_current_timezone())


class JanelaTests(BaseCalendario):
    def test_abre_30_min_antes_e_fecha_60_depois(self):
        treino = self.evento(dias=0)   # 18h às 20h
        inicio, fim = janela(treino)
        self.assertEqual((inicio.time(), fim.time()), (time(17, 30), time(21, 0)))
        self.assertFalse(dentro_da_janela(treino, as_(17, 29)))
        self.assertTrue(dentro_da_janela(treino, as_(17, 30)))
        self.assertTrue(dentro_da_janela(treino, as_(21, 0)))
        self.assertFalse(dentro_da_janela(treino, as_(21, 1)))

    def test_nao_passa_da_meia_noite(self):
        treino = self.evento(dias=0, hora_inicio=time(22), hora_fim=time(23, 30))
        self.assertEqual(janela(treino)[1].time(), time(23, 59, 59))


@patch("calendario.regras.timezone.now", return_value=as_(19))
class PresencaTests(BaseCalendario):
    def setUp(self):
        super().setUp()
        self.carla = criar_atleta("carla@usp.br", "Carla Dias", 1003)
        self.treino = self.evento(dias=0)   # hoje, 18h às 20h → janela 17h30–21h
        self.url = f"/api/v1/eventos/{self.treino.id}/presencas/"
        self.entrar(self.ana)

    def test_confirmar_minha_presenca(self, _):
        r = self.client.post(self.url, {}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data, {"registrados": [self.ana.id], "ja_presentes": []})
        p = Presenca.objects.get(evento=self.treino, atleta=self.ana)
        self.assertEqual(p.registrado_por, self.ana)
        self.assertIn(self.ana, self.treino.presentes.all())   # n×n atleta × evento
        self.assertFalse(Notificacao.objects.exists())          # ninguém é avisado da própria presença

    def test_adicionar_colegas_notifica_e_guarda_o_autor(self, _):
        r = self.client.post(self.url, {"atletas": [self.carla.id, self.bruno.id]}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(sorted(r.data["registrados"]), sorted([self.carla.id, self.bruno.id]))
        self.assertEqual(Presenca.objects.get(atleta=self.carla).registrado_por, self.ana)
        avisados = set(Notificacao.objects.filter(tipo="presenca_registrada").values_list("destinatario", flat=True))
        self.assertEqual(avisados, {self.carla.id, self.bruno.id})

    def test_ja_presente_nao_duplica(self, _):
        self.client.post(self.url, {}, format="json")
        r = self.client.post(self.url, {"atletas": [self.ana.id, self.carla.id]}, format="json")
        self.assertEqual(r.data, {"registrados": [self.carla.id], "ja_presentes": [self.ana.id]})
        self.assertEqual(Presenca.objects.filter(atleta=self.ana).count(), 1)

    def test_fora_da_janela(self, agora):
        agora.return_value = as_(21, 30)
        r = self.client.post(self.url, {}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["codigo"], "fora_da_janela")
        self.assertEqual(r.data["detail"], "O registro de presença para este treino está disponível das 17:30 às "
                                           "21:00. Para ajustes fora desse horário, procure a Diretoria")
        self.assertFalse(Presenca.objects.exists())

    def test_treino_de_outro_dia_esta_fora_da_janela(self, _):
        amanha = self.evento(dias=1)
        r = self.client.post(f"/api/v1/eventos/{amanha.id}/presencas/", {}, format="json")
        self.assertEqual(r.data["codigo"], "fora_da_janela")

    def test_treino_cancelado(self, _):
        self.treino.status = Evento.Status.CANCELADO
        self.treino.save()
        r = self.client.post(self.url, {}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual((r.data["codigo"], r.data["detail"]), ("evento_cancelado", "Este treino foi cancelado"))

    def test_atividade_nao_tem_presenca(self, _):
        atividade = self.evento(dias=0, tipo="atividade")
        r = self.client.post(f"/api/v1/eventos/{atividade.id}/presencas/", {}, format="json")
        self.assertEqual((r.status_code, r.data["codigo"]), (400, "nao_e_treino"))

    def test_colega_inativo_ou_inexistente(self, _):
        inativo = criar_atleta("ivo@usp.br", "Ivo Inativo", 1009, situacao="inativa")
        for ids in ([inativo.id], [9999]):
            r = self.client.post(self.url, {"atletas": ids}, format="json")
            self.assertEqual((r.status_code, r.data["codigo"]), (400, "atleta_invalido"))
        self.assertFalse(Presenca.objects.exists())

    def test_listar_presencas(self, _):
        self.client.post(self.url, {"atletas": [self.ana.id, self.carla.id]}, format="json")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["janela"], {"inicio": "17:30", "fim": "21:00"})
        self.assertTrue(r.data["dentro_da_janela"])
        self.assertEqual(r.data["evento"]["total_presentes"], 2)
        self.assertTrue(r.data["evento"]["presente"])
        item = r.data["presencas"][0]
        self.assertEqual(set(item), {"atleta", "registrado_por", "data_registro"})
        self.assertEqual(item["registrado_por"]["id"], self.ana.id)

    # --- remover (UC09-b) ---
    def test_autor_remove_dentro_da_janela(self, _):
        self.client.post(self.url, {"atletas": [self.carla.id]}, format="json")
        r = self.client.delete(f"{self.url}{self.carla.id}/")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Presenca.objects.exists())

    def test_quem_nao_e_autor_nao_remove(self, _):
        self.client.post(self.url, {"atletas": [self.carla.id]}, format="json")
        self.entrar(self.carla)   # a própria Carla não foi quem registrou
        r = self.client.delete(f"{self.url}{self.carla.id}/")
        self.assertEqual((r.status_code, r.data["codigo"]), (403, "nao_e_autor"))

    def test_autor_nao_remove_fora_da_janela_mas_diretor_sim(self, agora):
        self.client.post(self.url, {}, format="json")
        agora.return_value = as_(22)
        r = self.client.delete(f"{self.url}{self.ana.id}/")
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "fora_da_janela"))
        self.entrar(self.marina)
        self.assertEqual(self.client.delete(f"{self.url}{self.ana.id}/").status_code, 204)

    def test_remover_presenca_inexistente(self, _):
        self.assertEqual(self.client.delete(f"{self.url}{self.carla.id}/").status_code, 404)
