from datetime import date
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from contas.models import Curso
from partidas.models import Partida, SetPartida, AdversarioExterno
from desempenho import consultas
from desempenho.tests import test_dashboard_api


class EquipeAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Mesmo cenário de campeonato usado no dashboard individual.
        test_dashboard_api.DashboardAPITests.setUpTestData.__func__(cls)
        for _ in range(4):
            cls.criar_jogo(cls.bruno, cls.ana)
        cls.externo = AdversarioExterno.objects.create(nome='Visitante')

    @classmethod
    def criar_jogo(cls, atleta, adversario=None, status='confirmada', data=date(2026, 9, 20), campeonato=None, externo=None):
        partida = Partida.objects.create(atleta=atleta, adversario=adversario,
            tipo_adversario='externo' if externo else 'poli', adversario_externo=externo,
            formato=3, data_jogo=data, status=status, campeonato=campeonato)
        for numero in (1, 2):
            SetPartida.objects.create(partida=partida, numero=numero, pontos_atleta=11, pontos_adversario=5)
        return partida

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.diretor)
        relogio = patch('django.utils.timezone.localdate', return_value=date(2026, 11, 23))
        relogio.start()
        self.addCleanup(relogio.stop)

    def get(self, **params):
        return self.client.get('/api/v1/desempenho/equipe/', params)

    def test_contrato_perspectivas_e_contagem_unica(self):
        resposta = self.get()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(set(resposta.data), {'ranking', 'partidas_por_mes'})
        ranking = resposta.data['ranking']
        self.assertEqual([x['atleta']['id'] for x in ranking], [self.bruno.pk, self.ana.pk])
        self.assertEqual([x['vitorias'] for x in ranking], [5, 0])
        self.assertEqual([x['saldo_sets'] for x in ranking], [10, -10])
        self.assertEqual([x['posicao'] for x in ranking], [1, 2])
        self.assertEqual(sum(x['partidas'] for x in resposta.data['partidas_por_mes']), 5)
        self.assertEqual(len(resposta.data['partidas_por_mes']), 12)
        self.assertEqual(resposta.data['partidas_por_mes'][-1]['partidas'], 0)

    def test_permissoes(self):
        for usuario, status in [(None, 401), (self.ana, 403), (self.inativo, 403)]:
            self.client.force_authenticate(usuario)
            self.assertEqual(self.get().status_code, status)
        self.diretor.situacao = 'inativa'
        self.diretor.save()
        self.client.force_authenticate(self.diretor)
        self.assertEqual(self.get().status_code, 403)

    def test_minimo_cinco_e_filtro_competicao(self):
        for filtro, total in [('amistoso', 4), (str(self.copa.pk), 1), ('999999', 0)]:
            dados = self.get(competicao=filtro).data
            self.assertEqual(dados['ranking'], [])
            self.assertEqual(sum(x['partidas'] for x in dados['partidas_por_mes']), total)

    def test_externos_e_atletas_inativos_no_historico(self):
        self.ana.situacao = 'inativa'
        self.ana.save()
        self.criar_jogo(self.ana, externo=self.externo)
        dados = self.get().data
        self.assertEqual(dados['ranking'][1]['partidas'], 6)
        self.assertEqual(dados['ranking'][1]['vitorias'], 1)
        self.assertEqual(sum(x['partidas'] for x in dados['partidas_por_mes']), 6)

    def test_so_confirmadas_e_ate_hoje(self):
        for status in ['pendente', 'contestada', 'removida']:
            self.criar_jogo(self.ana, self.bruno, status=status)
        self.criar_jogo(self.ana, self.bruno, data=date(2026, 12, 1))
        self.assertEqual(self.get().data['ranking'][0]['partidas'], 5)

    def test_periodos_e_datas_inclusivas(self):
        for periodo, meses in [('3m', 3), ('6m', 6), ('12m', 12), ('tudo', 3)]:
            self.assertEqual(len(self.get(periodo=periodo).data['partidas_por_mes']), meses)
        dados = self.get(periodo='custom', inicio='2026-09-20', fim='2026-09-20').data
        self.assertEqual(dados['partidas_por_mes'], [{'mes': '2026-09', 'partidas': 5}])
        self.assertEqual(self.get(periodo='custom', inicio='2026-07-01', fim='2026-07-31').data['ranking'], [])

    def test_filtros_invalidos(self):
        for params in [dict(periodo='errado'), dict(competicao='abc'), dict(competicao='0'),
                       dict(periodo='custom'), dict(periodo='custom', inicio='2026-09-21', fim='2026-09-20'),
                       dict(periodo='custom', inicio='2026-09-01', fim='2026-12-01')]:
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 400)

    def test_parametros_individuais_nao_restringem_equipe(self):
        self.assertEqual(self.get(tipo_adversario='externo', atleta=self.diretor.pk).data, self.get().data)

    def test_consulta_em_lote_duas_queries(self):
        with self.assertNumQueries(2):
            grupos = consultas.linhas_da_equipe(date(2026, 1, 1), date(2026, 11, 23))
        self.assertEqual(len(grupos), 2)
        self.criar_jogo(self.diretor, self.inativo)
        with self.assertNumQueries(2):
            grupos = consultas.linhas_da_equipe(date(2026, 1, 1), date(2026, 11, 23))
        self.assertEqual(len(grupos), 4)

    def test_tudo_sem_partidas(self):
        SetPartida.objects.all().delete()
        Partida.objects.all().delete()
        self.assertEqual(self.get(periodo='tudo').data, {
            'ranking': [], 'partidas_por_mes': [{'mes': '2026-11', 'partidas': 0}]})

    def test_somente_leitura(self):
        self.assertEqual(self.client.post('/api/v1/desempenho/equipe/', {}).status_code, 405)
