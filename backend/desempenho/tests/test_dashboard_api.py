from datetime import date, datetime, timezone as tz
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from contas.models import Curso
from competicoes.models import Campeonato, Categoria, Inscricao
from partidas.models import Partida, SetPartida


class DashboardAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def usuario(nome, nusp, papel='atleta', situacao='ativa'):
            return get_user_model().objects.create_user(
                email=nome+'@usp.br', password='senha123', nome=nome, nusp=nusp,
                curso=Curso.objects.first(), ano_ingresso=2024, papel=papel, situacao=situacao,
            )
        cls.ana = usuario('Ana', 101)
        cls.bruno = usuario('Bruno', 102)
        cls.diretor = usuario('Diretor', 103, 'diretor')
        cls.inativo = usuario('Inativo', 104, situacao='inativa')
        cls.copa = Campeonato.objects.create(
            nome='Copa', organizador='Poli', local_campeonato='CEPEUSP',
            data_inicio=date(2026, 9, 19), data_fim=date(2026, 9, 20),
            abertura_inscricoes=datetime(2026, 8, 1, tzinfo=tz.utc),
            encerramento_inscricoes=datetime(2026, 9, 1, tzinfo=tz.utc),
            status='finalizado', criado_por=cls.diretor,
        )
        cat = Categoria.objects.create(campeonato=cls.copa, nome='Feminino')
        Inscricao.objects.create(categoria=cat, atleta=cls.ana, inscrito_por=cls.ana, colocacao=3, destaque='Bronze')
        cls.jogo = Partida.objects.create(
            atleta=cls.bruno, adversario=cls.ana, tipo_adversario='poli',
            formato=3, data_jogo=date(2026, 9, 20), status='confirmada', campeonato=cls.copa,
        )
        for numero in (1, 2):
            SetPartida.objects.create(partida=cls.jogo, numero=numero, pontos_atleta=11, pontos_adversario=5)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.ana)
        relogio = patch('django.utils.timezone.localdate', return_value=date(2026, 11, 23))
        relogio.start()
        self.addCleanup(relogio.stop)

    def get(self, **params):
        return self.client.get('/api/v1/desempenho/', params)

    def test_contrato_padrao_e_perspectiva(self):
        resposta = self.get()
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertEqual(set(dados), {'atleta', 'filtros', 'indicadores', 'evolucao_mensal', 'por_competicao', 'colocacoes', 'recentes', 'mais_enfrentados'})
        self.assertEqual(dados['filtros']['inicio'], '2025-12-01')
        self.assertEqual(dados['indicadores']['derrotas'], 1)
        self.assertEqual(dados['indicadores']['pontos_pro'], 10)
        self.assertEqual(dados['recentes'][0]['placar'], '0–2')
        self.assertEqual(len(dados['evolucao_mensal']), 12)
        self.assertIsNone(dados['evolucao_mensal'][-1]['pct_vitorias'])
        self.assertEqual(dados['colocacoes'][0]['destaque'], 'Bronze')

    def test_atleta_ignora_parametro_de_outro(self):
        for valor in (self.bruno.pk, 'invalido', 999999):
            with self.subTest(valor=valor):
                resposta = self.get(atleta=valor)
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.data['atleta']['id'], self.ana.pk)

    def test_diretor_consulta_outro(self):
        self.client.force_authenticate(self.diretor)
        resposta = self.get(atleta=self.bruno.pk)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data['indicadores']['vitorias'], 1)
        self.assertEqual(resposta.data['atleta']['id'], self.bruno.pk)

    def test_diretor_id_invalido_e_inexistente(self):
        self.client.force_authenticate(self.diretor)
        self.assertEqual(self.get(atleta='abc').status_code, 400)
        self.assertEqual(self.get(atleta=999999).status_code, 404)

    def test_autenticacao_e_conta_inativa(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.get().status_code, 401)
        self.client.force_authenticate(self.inativo)
        self.assertEqual(self.get().status_code, 403)

    def test_vazio(self):
        self.client.force_authenticate(self.diretor)
        dados = self.get().data
        self.assertEqual(dados['indicadores']['partidas'], 0)
        self.assertEqual(dados['recentes'], [])
        self.assertTrue(all(m['pct_vitorias'] is None for m in dados['evolucao_mensal']))

    def test_periodos(self):
        for periodo, inicio in [('3m', '2026-09-01'), ('6m', '2026-06-01'), ('tudo', '2026-09-20')]:
            with self.subTest(periodo=periodo):
                self.assertEqual(self.get(periodo=periodo).json()['filtros']['inicio'], inicio)

    def test_tudo_sem_historico(self):
        self.client.force_authenticate(self.diretor)
        self.assertEqual(self.get(periodo='tudo').json()['filtros']['inicio'], '2026-11-01')

    def test_custom_inclusivo(self):
        dados = self.get(periodo='custom', inicio='2026-09-20', fim='2026-09-20').data
        self.assertEqual(dados['indicadores']['partidas'], 1)

    def test_filtros_invalidos(self):
        for params, campo in [
            ({'periodo':'abc'}, 'periodo'), ({'competicao':'abc'}, 'competicao'),
            ({'tipo_adversario':'abc'}, 'tipo_adversario'),
            ({'periodo':'custom'}, 'inicio'),
            ({'periodo':'custom','inicio':'abc','fim':'2026-11-01'}, 'inicio'),
            ({'periodo':'custom','inicio':'2026-11-02','fim':'2026-11-01'}, 'fim'),
            ({'periodo':'custom','inicio':'2026-11-02','fim':'2026-11-24'}, 'fim'),
        ]:
            with self.subTest(params=params):
                resposta = self.get(**params)
                self.assertEqual(resposta.status_code, 400)
                self.assertIn(campo, resposta.data)

    def test_competicao_e_adversario(self):
        self.assertEqual(self.get(competicao=self.copa.pk).data['indicadores']['partidas'], 1)
        dados = self.get(competicao='amistoso').data
        self.assertEqual(dados['indicadores']['partidas'], 0)
        self.assertEqual(dados['colocacoes'], [])
        self.assertEqual(self.get(tipo_adversario='externo').data['indicadores']['partidas'], 0)

    def test_colocacoes_filtradas(self):
        dados = self.get(periodo='custom', inicio='2026-11-01', fim='2026-11-23').data
        self.assertEqual(dados['colocacoes'], [])
        Inscricao.objects.update(status='cancelada')
        self.assertEqual(self.get().data['colocacoes'], [])

    def test_pendentes_nao_entram_nem_definem_inicio(self):
        Partida.objects.filter(pk=self.jogo.pk).update(status='pendente')
        dados = self.get(periodo='tudo').json()
        self.assertEqual(dados['indicadores']['partidas'], 0)
        self.assertEqual(dados['filtros']['inicio'], '2026-11-01')

    def test_sem_escrita(self):
        self.assertEqual(self.client.post('/api/v1/desempenho/', {}).status_code, 405)
