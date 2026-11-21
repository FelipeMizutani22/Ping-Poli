"""Testes das regras que o BANCO garante para partidas e sets (constraints do ER)."""
from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from contas.models import Curso
from partidas.models import AdversarioExterno, Contestacao, Partida, SetPartida


def criar_atleta(email, nusp):
    curso = Curso.objects.first()
    return get_user_model().objects.create_user(
        email, "pingpoli123", nome=email.split("@")[0], nusp=nusp, curso=curso, ano_ingresso=2024
    )


class RegrasDoBancoTests(TestCase):
    def setUp(self):
        self.ana = criar_atleta("ana@usp.br", 1)
        self.bruno = criar_atleta("bruno@usp.br", 2)
        self.externo = AdversarioExterno.objects.create(nome="Carlos Pereira", clube="ECP")
        self.partida = self.nova_partida(adversario=self.bruno)

    def nova_partida(self, **campos):
        dados = {"atleta": self.ana, "tipo_adversario": "poli", "formato": 5,
                 "data_jogo": date(2026, 11, 18), "status": "pendente"}
        dados.update(campos)
        with transaction.atomic():
            return Partida.objects.create(**dados)

    def assertRecusado(self, funcao):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                funcao()

    # --- regra do set: 11 pontos com 2 de vantagem ---
    def test_sets_validos_sao_aceitos(self):
        for n, (a, b) in enumerate([(11, 9), (9, 11), (12, 10), (13, 11), (11, 0)], start=1):
            SetPartida.objects.create(partida=self.partida, numero=n, pontos_atleta=a, pontos_adversario=b)
        self.assertEqual(self.partida.sets_oficiais().count(), 5)

    def test_sets_invalidos_sao_recusados(self):
        for a, b in [(11, 10), (10, 8), (12, 9), (15, 11), (11, 11)]:
            with self.subTest(placar=f"{a}x{b}"):
                self.assertRecusado(lambda: SetPartida.objects.create(
                    partida=self.partida, numero=1, pontos_atleta=a, pontos_adversario=b))

    def test_set_oficial_nao_se_repete_mas_proposto_pode(self):
        SetPartida.objects.create(partida=self.partida, numero=1, pontos_atleta=11, pontos_adversario=5)
        self.assertRecusado(lambda: SetPartida.objects.create(
            partida=self.partida, numero=1, pontos_atleta=11, pontos_adversario=3))
        contestacao = Contestacao.objects.create(partida=self.partida, contestante=self.bruno,
                                                 justificativa="O placar do set 1 foi outro")
        SetPartida.objects.create(partida=self.partida, contestacao=contestacao, numero=1,
                                  pontos_atleta=5, pontos_adversario=11)
        self.assertEqual(self.partida.sets_oficiais().count(), 1)

    # --- adversário exclusivo {xor} ---
    def test_partida_contra_externo_e_aceita(self):
        p = self.nova_partida(tipo_adversario="externo", adversario_externo=self.externo, status="confirmada")
        self.assertIsNone(p.adversario)

    def test_partida_com_os_dois_adversarios_e_recusada(self):
        self.assertRecusado(lambda: self.nova_partida(adversario=self.bruno, adversario_externo=self.externo))

    def test_partida_sem_adversario_e_recusada(self):
        self.assertRecusado(lambda: self.nova_partida())

    def test_partida_contra_si_mesmo_e_recusada(self):
        self.assertRecusado(lambda: self.nova_partida(adversario=self.ana))

    def test_formato_invalido_e_recusado(self):
        self.assertRecusado(lambda: self.nova_partida(adversario=self.bruno, formato=4))