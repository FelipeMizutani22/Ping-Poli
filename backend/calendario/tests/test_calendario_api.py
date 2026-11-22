"""Testes da API de calendário e eventos (UC07, UC08 · C5)."""
from datetime import time, timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.db import models
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from calendario.models import Evento, Presenca
from competicoes.models import Campeonato
from nucleo.models import Notificacao
from partidas.tests.test_partidas_api import criar_atleta

HOJE = timezone.localdate


class BaseCalendario(APITestCase):
    def setUp(self):
        self.ana = criar_atleta("ana@usp.br", "Ana Lima", 1001)
        self.bruno = criar_atleta("bruno@usp.br", "Bruno Kato", 1002)
        self.marina = criar_atleta("marina@usp.br", "Marina Diretora", 1004, papel="diretor")
        self.entrar(self.marina)

    def entrar(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def evento(self, dias=1, **campos):
        dados = dict(tipo="treino", titulo="Treino", data_evento=HOJE() + timedelta(days=dias),
                     hora_inicio=time(18), hora_fim=time(20), local_evento="CEPEUSP – Ginásio",
                     criado_por=self.marina)
        dados.update(campos)
        return Evento.objects.create(**dados)

    def dados(self, **mudancas):
        base = {"tipo": "treino", "titulo": "Treino técnico", "data_evento": (HOJE() + timedelta(days=2)).isoformat(),
                "hora_inicio": "18:00", "hora_fim": "20:00", "local_evento": "CEPEUSP – Ginásio"}
        base.update(mudancas)
        return base


class CalendarioTests(BaseCalendario):
    def setUp(self):
        super().setUp()
        self.treino = self.evento(dias=1)
        self.atividade = self.evento(dias=3, tipo="atividade", titulo="Palestra", hora_inicio=time(19))
        self.fora = self.evento(dias=60)
        agora = timezone.now()
        self.copa = Campeonato.objects.create(
            nome="Copa Poli", organizador="Poli", local_campeonato="CEPEUSP",
            data_inicio=HOJE() - timedelta(days=1), data_fim=HOJE() + timedelta(days=1),
            abertura_inscricoes=agora - timedelta(days=10), encerramento_inscricoes=agora - timedelta(days=5),
            criado_por=self.marina,
        )
        Presenca.objects.create(evento=self.treino, atleta=self.ana, registrado_por=self.ana)
        self.entrar(self.ana)

    def periodo(self, **extra):
        return {"inicio": HOJE().isoformat(), "fim": (HOJE() + timedelta(days=10)).isoformat(), **extra}

    def test_une_eventos_e_campeonatos_em_ordem(self):
        r = self.client.get("/api/v1/calendario/", self.periodo())
        self.assertEqual(r.status_code, 200)
        self.assertEqual([(i["tipo"], i["id"]) for i in r.data],
                         [("campeonato", self.copa.id), ("treino", self.treino.id), ("atividade", self.atividade.id)])

    def test_formato_dos_itens(self):
        itens = {i["tipo"]: i for i in self.client.get("/api/v1/calendario/", self.periodo()).data}
        treino = itens["treino"]
        self.assertEqual(treino["hora_inicio"], "18:00")
        self.assertEqual(treino["local"], "CEPEUSP – Ginásio")
        self.assertEqual(treino["status"], "agendado")
        self.assertTrue(treino["presente"])
        self.assertFalse(itens["atividade"]["presente"])
        campeonato = itens["campeonato"]   # começou antes do período, mas ocupa dias dentro dele
        self.assertEqual(campeonato["data_fim"], (HOJE() + timedelta(days=1)).isoformat())
        self.assertEqual(campeonato["titulo"], "Copa Poli")

    def test_filtro_por_tipo(self):
        r = self.client.get("/api/v1/calendario/", self.periodo(tipo="campeonato"))
        self.assertEqual([i["tipo"] for i in r.data], ["campeonato"])
        r = self.client.get("/api/v1/calendario/", self.periodo(tipo="treino"))
        self.assertEqual([i["id"] for i in r.data], [self.treino.id])
        self.assertEqual(self.client.get("/api/v1/calendario/", self.periodo(tipo="festa")).status_code, 400)

    def test_sem_periodo_usa_o_mes_atual(self):
        r = self.client.get("/api/v1/calendario/")
        self.assertEqual(r.status_code, 200)
        for item in r.data:
            if item["tipo"] != "campeonato":
                self.assertEqual(item["data"][:7], HOJE().isoformat()[:7])

    def test_cancelado_continua_no_calendario(self):
        self.treino.status = "cancelado"
        self.treino.save()
        itens = self.client.get("/api/v1/calendario/", self.periodo(tipo="treino")).data
        self.assertEqual(itens[0]["status"], "cancelado")

    def test_detalhe_do_evento(self):
        r = self.client.get(f"/api/v1/eventos/{self.treino.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["hora_fim"], "20:00")
        self.assertEqual(r.data["total_presentes"], 1)
        self.assertTrue(r.data["presente"])
        self.assertEqual(r.data["criado_por"]["id"], self.marina.id)

    def test_anonimo_nao_ve(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/calendario/").status_code, 401)


class GerenciarEventosTests(BaseCalendario):
    def test_diretor_cria_evento(self):
        r = self.client.post("/api/v1/eventos/", self.dados(descricao="Saque e recepção"), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        evento = Evento.objects.get(pk=r.data["id"])
        self.assertEqual((evento.status, evento.criado_por), ("agendado", self.marina))
        self.assertEqual(r.data["hora_inicio"], "18:00")

    def test_atleta_nao_cria_nem_edita_nem_cancela(self):
        evento = self.evento()
        self.entrar(self.ana)
        self.assertEqual(self.client.post("/api/v1/eventos/", self.dados(), format="json").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/v1/eventos/{evento.id}/", {"titulo": "X"}, format="json").status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/eventos/{evento.id}/cancelar/").status_code, 403)

    def test_validacoes(self):
        ontem = (HOJE() - timedelta(days=1)).isoformat()
        r = self.client.post("/api/v1/eventos/", self.dados(titulo="ab", tipo="campeonato", data_evento=ontem,
                                                           local_evento=""), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {"titulo", "tipo", "data_evento", "local_evento"})
        self.assertEqual(r.data["data_evento"], ["A data do evento deve ser hoje ou uma data futura"])

    def test_termino_antes_do_inicio(self):
        r = self.client.post("/api/v1/eventos/", self.dados(hora_inicio="20:00", hora_fim="18:00"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["hora_fim"], ["O horário de término deve ser posterior ao de início"])

    def test_editar_sem_mudar_local_nao_manda_email(self):
        evento = self.evento()
        r = self.client.patch(f"/api/v1/eventos/{evento.id}/", {"titulo": "Treino técnico"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["titulo"], "Treino técnico")
        self.assertEqual(mail.outbox, [])

    def test_editar_horario_avisa_por_email(self):
        evento = self.evento()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.patch(f"/api/v1/eventos/{evento.id}/", {"hora_inicio": "19:00", "hora_fim": "21:00"},
                                  format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 3)

    def test_editar_horario_invalido_considera_o_valor_salvo(self):
        evento = self.evento()   # 18h às 20h
        r = self.client.patch(f"/api/v1/eventos/{evento.id}/", {"hora_inicio": "21:00"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_editar_evento_passado_sem_mudar_a_data(self):
        evento = self.evento(dias=-7)
        r = self.client.patch(f"/api/v1/eventos/{evento.id}/",
                              {"titulo": "Treino de ontem", "data_evento": evento.data_evento.isoformat()}, format="json")
        self.assertEqual(r.status_code, 200, r.data)

    def test_cancelar_notifica_e_continua_visivel(self):
        evento = self.evento()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(f"/api/v1/eventos/{evento.id}/cancelar/", {"motivo": "Ginásio interditado"},
                                 format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data["status"], r.data["motivo_cancelamento"]), ("cancelado", "Ginásio interditado"))
        self.assertEqual(Notificacao.objects.filter(tipo="evento_cancelado").count(), 3)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(self.client.get(f"/api/v1/eventos/{evento.id}/").status_code, 200)

    def test_cancelar_sem_motivo_e_duas_vezes(self):
        evento = self.evento()
        self.assertEqual(self.client.post(f"/api/v1/eventos/{evento.id}/cancelar/").status_code, 200)
        r = self.client.post(f"/api/v1/eventos/{evento.id}/cancelar/")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["codigo"], "ja_cancelado")

    def test_evento_inexistente(self):
        self.assertEqual(self.client.get("/api/v1/eventos/999/").status_code, 404)
        self.assertEqual(self.client.post("/api/v1/eventos/999/cancelar/").status_code, 404)


class SeedCalendarioTests(TestCase):
    def test_treinos_ter_qui_e_treino_de_hoje(self):
        call_command("seed_demo", stdout=StringIO())
        regulares = Evento.objects.filter(titulo="Treino da equipe")
        self.assertTrue(regulares.exists())
        self.assertTrue(all(e.data_evento.weekday() in (1, 3) for e in regulares))
        self.assertEqual(min(e.data_evento for e in regulares) >= HOJE() - timedelta(weeks=8), True)
        hoje = Evento.objects.get(titulo="Treino livre")
        self.assertEqual(hoje.data_evento, HOJE())
        self.assertGreater(hoje.hora_fim, hoje.hora_inicio)
        self.assertTrue(Evento.objects.filter(tipo="atividade", data_evento=HOJE() + timedelta(days=10)).exists())

    def test_presencas_so_nos_treinos_passados(self):
        call_command("seed_demo", stdout=StringIO())
        self.assertTrue(Presenca.objects.filter(atleta__email="ana.lima@usp.br").exists())
        self.assertFalse(Presenca.objects.filter(evento__data_evento__gte=HOJE()).exists())
        self.assertTrue(Presenca.objects.exclude(registrado_por=models.F("atleta")).exists())   # registradas por colegas
