from datetime import date
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from contas.models import Curso
from partidas.models import Partida, SetPartida, AdversarioExterno


class ConfrontoAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def atleta(nome, nusp, **extra):
            return get_user_model().objects.create_user(email=f'{nome}@usp.br', password='senha123', nome=nome, nusp=nusp, curso=Curso.objects.first(), ano_ingresso=2024, situacao='ativa', **extra)
        cls.a = atleta('Ana', 101)
        cls.b = atleta('Bruno', 102)
        cls.c = atleta('Carla', 103)
        cls.d = atleta('Diretor', 104, papel='diretor')
        cls.j1 = cls.jogo(cls.b, cls.a, date(2025, 1, 1))
        cls.j2 = cls.jogo(cls.a, cls.b, date(2026, 10, 1))
        cls.j3 = cls.jogo(cls.a, cls.c, date(2026, 10, 2))
        cls.jogo(cls.b, cls.a, date(2026, 11, 1), status='pendente')
        cls.jogo(cls.a, cls.b, date(2026, 11, 2), status='contestada')
        cls.jogo(cls.a, cls.b, date(2026, 11, 3), status='removida')
        cls.jogo(cls.a, cls.b, date(2027, 1, 1))
        externo = AdversarioExterno.objects.create(nome='Externo')
        p = Partida.objects.create(atleta=cls.b, adversario_externo=externo, tipo_adversario='externo', formato=3, data_jogo=date(2026, 10, 3), status='confirmada')
        for n in (1, 2):
            SetPartida.objects.create(partida=p, numero=n, pontos_atleta=11, pontos_adversario=3)

    @staticmethod
    def jogo(a, b, data, status='confirmada'):
        p = Partida.objects.create(atleta=a, adversario=b, tipo_adversario='poli', formato=3, data_jogo=data, status=status)
        for n in (1, 2):
            SetPartida.objects.create(partida=p, numero=n, pontos_atleta=11, pontos_adversario=5)
        return p

    def setUp(self):
        self.client = APIClient(); self.client.force_authenticate(self.a)
        relogio = patch('django.utils.timezone.localdate', return_value=date(2026, 11, 23))
        relogio.start(); self.addCleanup(relogio.stop)

    def get(self, **params):
        return self.client.get('/api/v1/desempenho/confronto/', {'b': self.b.pk, **params})

    def test_contrato_historico_e_perspectivas(self):
        r = self.get(); self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d['retrospecto'], {'vitorias_a': 1, 'vitorias_b': 1, 'sets_a': 2, 'sets_b': 2, 'pontos_a': 32, 'pontos_b': 32, 'pct_a': 50.0, 'pct_b': 50.0})
        self.assertEqual([p['partida_id'] for p in d['partidas']], [self.j1.pk, self.j2.pk])
        self.assertEqual(d['partidas'][0]['sets'][0], {'numero': 1, 'pontos_atleta': 5, 'pontos_adversario': 11})
        self.assertEqual(d['partidas'][1]['sets'][0]['pontos_atleta'], 11)
        self.assertEqual(d['ultima_partida']['partida_id'], self.j2.pk)
        self.assertEqual(d['maior_vitoria_a']['partida_id'], self.j2.pk)
        self.assertEqual(d['maior_vitoria_b']['partida_id'], self.j1.pk)
        self.assertEqual(d['acumulado'][-1]['vitorias_a'], 1)
        self.assertEqual(d['acumulado'][-1]['vitorias_b'], 1)
        self.assertEqual(d['pendentes_entre_eles'], 1)

    def test_indicadores_gerais_incluem_outros_e_externos(self):
        d = self.get().data
        self.assertEqual(d['indicadores_a']['partidas'], 3)
        self.assertEqual(d['indicadores_a']['vitorias'], 2)
        self.assertEqual(d['indicadores_b']['partidas'], 3)
        self.assertEqual(d['indicadores_b']['vitorias'], 2)

    def test_atleta_nao_troca_a(self):
        for a in (self.c.pk, 'abc', 999999):
            self.assertEqual(self.get(a=a).data['a']['id'], self.a.pk)

    def test_diretor_troca_a(self):
        self.client.force_authenticate(self.d)
        r = self.get(a=self.c.pk, b=self.a.pk)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['a']['id'], self.c.pk)
        self.assertEqual(r.data['retrospecto']['vitorias_b'], 1)
        self.assertEqual(self.get(a='abc').status_code, 400)
        self.assertEqual(self.get(a=999999).status_code, 404)

    def test_sem_confronto_mantem_indicadores(self):
        d = self.get(b=self.d.pk).data
        self.assertEqual(d['partidas'], [])
        self.assertIsNone(d['ultima_partida'])
        self.assertEqual(d['indicadores_a']['partidas'], 3)
        self.assertEqual(d['indicadores_b']['partidas'], 0)

    def test_custom_e_pendentes_filtrados(self):
        d = self.get(periodo='custom', inicio='2026-10-01', fim='2026-10-01').data
        self.assertEqual(len(d['partidas']), 1)
        self.assertEqual(d['pendentes_entre_eles'], 0)
        self.assertEqual(d['indicadores_a']['partidas'], 1)

    def test_erros_de_entrada(self):
        self.assertEqual(self.client.get('/api/v1/desempenho/confronto/').status_code, 400)
        for params in ({'b': self.a.pk}, {'b': 'abc'}, {'b': 0}, {'b': '9'*30}, {'periodo': 'custom'}, {'periodo': 'custom', 'inicio': '2026-11-02', 'fim': '2026-11-01'}, {'periodo': 'custom', 'inicio': '2026-11-01', 'fim': '2027-01-01'}):
            self.assertEqual(self.get(**params).status_code, 400, params)
        self.assertEqual(self.get(b=999999).status_code, 404)

    def test_autenticacao_e_inativos(self):
        self.b.situacao = 'inativa'; self.b.save()
        self.assertEqual(self.get().status_code, 200)
        self.client.force_authenticate(None)
        self.assertEqual(self.get().status_code, 401)
        self.client.force_authenticate(self.b)
        self.assertEqual(self.get(b=self.a.pk).status_code, 403)

    def test_consultas_nao_crescem_por_partida(self):
        with self.assertNumQueries(8):
            self.get()
        for _ in range(5):
            self.jogo(self.a, self.b, date(2026, 10, 1))
        with self.assertNumQueries(8):
            self.get()

    def test_pendencia_anterior_ao_primeiro_confirmado(self):
        self.jogo(self.a, self.b, date(2024, 1, 1), status='pendente')
        self.assertEqual(self.get().data['pendentes_entre_eles'], 2)
