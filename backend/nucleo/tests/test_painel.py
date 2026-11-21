"""Testes do painel da página inicial (T03 Atleta / T04 Diretor)."""
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from avisos.models import Aviso, AvisoLeitura
from calendario.models import Evento, Presenca
from competicoes.models import Campeonato
from contas.models import Curso
from nucleo.servicos import notificar
from partidas.models import Partida

Atleta = get_user_model()
URL = "/api/v1/painel/"


def criar(email, nusp, papel="atleta", situacao="ativa"):
    return Atleta.objects.create_user(
        email, "pingpoli123", nome=email.split("@")[0].title(), nusp=nusp,
        curso=Curso.objects.first(), ano_ingresso=2024, papel=papel, situacao=situacao,
    )


class PainelTests(APITestCase):
    def setUp(self):
        self.hoje = timezone.localdate()
        self.marina = criar("marina@usp.br", 1, papel="diretor")
        self.ana = criar("ana@usp.br", 2)
        self.bruno = criar("bruno@usp.br", 3)
        criar("julia@usp.br", 4, situacao="pendente")

        aviso = lambda titulo, **kw: Aviso.objects.create(autor=self.marina, titulo=titulo, conteudo="x" * 300, **kw)
        self.fixado = aviso("Treino extra", fixado=True)
        aviso("Fixado expirado", fixado=True, data_expiracao=self.hoje - timedelta(days=1))
        aviso("Fixado excluído", fixado=True, excluido=True)
        aviso("Não fixado")
        AvisoLeitura.objects.create(aviso=self.fixado, atleta=self.ana)

        evento = lambda dias, **kw: Evento.objects.create(
            tipo="treino", titulo=f"Treino +{dias}", data_evento=self.hoje + timedelta(days=dias),
            hora_inicio=time(18), hora_fim=time(20), local_evento="CEPEUSP", criado_por=self.marina, **kw)
        self.treino = evento(2)
        evento(1, status="cancelado")
        evento(45)
        evento(-3)
        Presenca.objects.create(evento=self.treino, atleta=self.ana, registrado_por=self.ana)
        Campeonato.objects.create(
            nome="Copa Poli", organizador="AAAP", local_campeonato="Poli",
            data_inicio=self.hoje + timedelta(days=10), data_fim=self.hoje + timedelta(days=11),
            abertura_inscricoes=timezone.now(), encerramento_inscricoes=timezone.now() + timedelta(days=5),
            criado_por=self.marina,
        )

        partida = lambda **kw: Partida.objects.create(
            atleta=self.bruno, tipo_adversario="poli", formato=5, data_jogo=date(2026, 11, 1), **kw)
        partida(adversario=self.ana, status="pendente")
        partida(adversario=self.ana, status="contestada")
        notificar(self.ana, "partida_pendente", "Bruno registrou uma partida")

    def get_como(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200)
        return r.data

    def test_painel_do_atleta(self):
        p = self.get_como(self.ana)
        self.assertEqual([a["titulo"] for a in p["avisos_fixados"]], ["Treino extra"])
        self.assertTrue(p["avisos_fixados"][0]["lido"])
        self.assertEqual(len(p["avisos_fixados"][0]["trecho"]), 200)
        self.assertEqual([e["titulo"] for e in p["proximos_eventos"]], ["Treino +2", "Copa Poli"])
        self.assertTrue(p["proximos_eventos"][0]["presente"])
        self.assertEqual(p["partidas_pendentes"], 1)
        self.assertEqual(p["notificacoes_nao_lidas"], 1)
        self.assertIsNone(p["admin"])

    def test_painel_do_diretor_tem_contadores(self):
        p = self.get_como(self.marina)
        self.assertEqual(p["admin"], {"solicitacoes_pendentes": 1, "partidas_contestadas": 1})
        self.assertFalse(p["avisos_fixados"][0]["lido"])

    def test_sem_login(self):
        self.assertEqual(self.client.get(URL).status_code, 401)