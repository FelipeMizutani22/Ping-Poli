from datetime import datetime, timedelta, timezone as tz
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from avisos.models import Aviso
from contas.models import Curso
from nucleo.models import Auditoria, Notificacao
from partidas.models import Partida
from competicoes.models import Campeonato, Categoria, Inscricao
from competicoes.servicos import sincronizar_status
from competicoes.views import campeonatos_para
from competicoes.serializers import CampeonatoSerializer

AGORA = datetime(2026, 11, 23, 15, tzinfo=tz.utc)


class CampeonatosAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def usuario(nome, nusp, papel='atleta', situacao='ativa'):
            return get_user_model().objects.create_user(email=f'{nome}@usp.br', password='senha123',
                nome=nome, nusp=nusp, ano_ingresso=2024, curso=Curso.objects.first(), papel=papel, situacao=situacao)
        cls.ana = usuario('Ana', 801)
        cls.bruno = usuario('Bruno', 802)
        cls.diretor = usuario('Diretor', 803, 'diretor')
        cls.inativo = usuario('Inativo', 804, situacao='inativa')

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.diretor)
        relogio = patch('django.utils.timezone.now', return_value=AGORA)
        relogio.start()
        self.addCleanup(relogio.stop)

    def payload(self, **mudancas):
        dados = dict(nome='Copa Poli', organizador='AAAP', local_campeonato='CEPEUSP',
            data_inicio='2026-12-05', data_fim='2026-12-06',
            abertura_inscricoes='2026-11-25T12:00:00-03:00', encerramento_inscricoes='2026-12-04T18:00:00-03:00',
            valor_inscricao='30.00', categorias=[{'nome': 'Feminino', 'vagas': 2}, {'nome': 'Livre', 'vagas': None}])
        dados.update(mudancas)
        return dados

    def criar(self, **mudancas):
        resposta = self.client.post('/api/v1/campeonatos/', self.payload(**mudancas), format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        return Campeonato.objects.get(pk=resposta.data['id'])

    def detalhe(self, c):
        return f'/api/v1/campeonatos/{c.pk}/'

    def inscrever(self, categoria, atleta=None, status='ativa'):
        return Inscricao.objects.create(categoria=categoria, atleta=atleta or self.ana,
            inscrito_por=self.diretor, status=status)

    def test_criacao_contrato_aviso_e_autor(self):
        c = self.criar()
        resposta = self.client.get(self.detalhe(c))
        self.assertEqual(set(resposta.data), {'id', 'nome', 'organizador', 'local_campeonato', 'data_inicio',
            'data_fim', 'abertura_inscricoes', 'encerramento_inscricoes', 'valor_inscricao',
            'link_regulamento', 'observacoes', 'status', 'categorias', 'inscrito'})
        self.assertEqual(c.criado_por, self.diretor)
        self.assertEqual(c.status, 'planejado')
        self.assertEqual(c.categorias.count(), 2)
        self.assertEqual(Aviso.objects.get().categoria, 'campeonato')
        self.assertEqual(resposta.data['valor_inscricao'], '30.00')
        self.assertFalse(resposta.data['inscrito'])

    def test_criacao_aberta_e_sem_anuncio(self):
        c = self.criar(abertura_inscricoes=(AGORA-timedelta(days=1)).isoformat(), anunciar=False)
        self.assertEqual(c.status, 'inscricoes_abertas')
        self.assertEqual(Aviso.objects.count(), 0)
        self.assertEqual(Notificacao.objects.filter(tipo='inscricoes_abertas').count(), 3)
        self.assertEqual(sincronizar_status(), 0)
        self.assertEqual(Notificacao.objects.count(), 3)

    def test_leitura_permitida_e_escrita_restrita(self):
        c = self.criar()
        for usuario, esperado in [(None, 401), (self.inativo, 403), (self.ana, 200)]:
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get('/api/v1/campeonatos/').status_code, esperado)
            self.assertEqual(self.client.get(self.detalhe(c)).status_code, esperado)
            negado = 401 if usuario is None else 403
            self.assertEqual(self.client.post('/api/v1/campeonatos/', self.payload(), format='json').status_code, negado)
            self.assertEqual(self.client.patch(self.detalhe(c), {'nome': 'Outra Copa'}, format='json').status_code, negado)
            self.assertEqual(self.client.post(self.detalhe(c)+'cancelar/', {'motivo': 'Chuva muito forte'}, format='json').status_code, negado)

    def test_vagas_e_inscrito_sao_por_usuario_e_so_ativas(self):
        c = self.criar()
        categoria = c.categorias.get(nome='Feminino')
        self.inscrever(categoria)
        self.inscrever(categoria, self.bruno, 'cancelada')
        self.client.force_authenticate(self.ana)
        dados = self.client.get(self.detalhe(c)).data
        self.assertTrue(dados['inscrito'])
        self.assertEqual(dados['categorias'][0]['vagas_restantes'], 1)
        self.assertTrue(dados['categorias'][0]['inscrito'])
        self.assertIsNone(dados['categorias'][1]['vagas_restantes'])
        self.client.force_authenticate(self.bruno)
        self.assertFalse(self.client.get(self.detalhe(c)).data['inscrito'])

    def test_filtro_e_sincronizacao_antes_da_listagem(self):
        c = self.criar()
        Campeonato.objects.filter(pk=c.pk).update(abertura_inscricoes=AGORA)
        dados = self.client.get('/api/v1/campeonatos/', {'status': 'inscricoes_abertas'}).data
        self.assertEqual([x['id'] for x in dados], [c.pk])
        self.assertEqual(self.client.get('/api/v1/campeonatos/', {'status': 'planejado'}).data, [])
        self.assertEqual(self.client.get('/api/v1/campeonatos/', {'status': 'invalido'}).status_code, 400)

    def test_validacoes_sem_gravacao_parcial(self):
        invalidos = [dict(nome='A'), dict(data_fim='2026-12-01'), dict(valor_inscricao='-1'),
            dict(encerramento_inscricoes='2026-12-06T12:00:00-03:00'),
            dict(encerramento_inscricoes='2026-11-25T12:00:00-03:00'),
            dict(categorias=[]), dict(categorias=[{'nome': 'A'}]), dict(categorias=[{'nome': 'Livre', 'vagas': 0}]),
            dict(categorias=[{'nome': 'Livre'}, {'nome': 'livre'}]),
            dict(categorias=[{'id': 1, 'nome': 'Livre'}]), dict(status='finalizado'), dict(link_regulamento='invalido')]
        for campos in invalidos:
            with self.subTest(campos=campos):
                resposta = self.client.post('/api/v1/campeonatos/', self.payload(**campos), format='json')
                self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertEqual(Campeonato.objects.count(), 0)
        self.assertEqual(Categoria.objects.count(), 0)
        self.assertEqual(Aviso.objects.count(), 0)

    def test_prazo_no_dia_inicio_fuso_brasilia(self):
        self.criar(encerramento_inscricoes='2026-12-06T01:00:00Z')  # 05/12 às 22h.

    def test_duplicidade_pede_confirmacao(self):
        self.criar()
        resposta = self.client.post('/api/v1/campeonatos/', self.payload(), format='json')
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.data['codigo'], 'possivel_duplicada')
        self.criar(confirmar_duplicada=True)
        self.assertEqual(Campeonato.objects.count(), 2)

    def test_patch_parcial_valida_datas_com_existentes(self):
        c = self.criar()
        self.assertEqual(self.client.patch(self.detalhe(c), {'data_inicio': '2026-12-07'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.detalhe(c), {'encerramento_inscricoes': '2026-11-24T12:00:00-03:00'}, format='json').status_code, 400)
        resposta = self.client.patch(self.detalhe(c), {'observacoes': 'Levar raquete'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(len(resposta.data['categorias']), 2)

    def test_editar_categorias_preserva_ids_e_troca_nomes(self):
        c = self.criar()
        a, b = list(c.categorias.all())
        itens = [{'id': a.pk, 'nome': b.nome, 'vagas': 3}, {'id': b.pk, 'nome': a.nome, 'vagas': None}, {'nome': 'Duplas'}]
        resposta = self.client.patch(self.detalhe(c), {'categorias': itens}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        a.refresh_from_db()
        self.assertEqual(a.nome, b.nome)
        self.assertEqual(c.categorias.count(), 3)

    def test_categoria_parcial_ou_de_outro_campeonato_rejeitada(self):
        c = self.criar()
        for itens in [[{'id': c.categorias.first().pk}], [{'id': 999999, 'nome': 'Livre'}]]:
            resposta = self.client.patch(self.detalhe(c), {'categorias': itens}, format='json')
            self.assertEqual(resposta.status_code, 400, resposta.data)
        self.assertEqual(c.categorias.count(), 2)

    def test_remocao_categoria_vinculada_bloqueada_e_rollback(self):
        c = self.criar()
        categoria = c.categorias.get(nome='Feminino')
        self.inscrever(categoria)
        resposta = self.client.patch(self.detalhe(c), {'nome': 'Nome alterado', 'categorias': [{'nome': 'Duplas'}]}, format='json')
        self.assertEqual(resposta.status_code, 409)
        c.refresh_from_db()
        self.assertEqual(c.nome, 'Copa Poli')
        self.assertEqual(c.categorias.count(), 2)

    def test_vagas_nao_podem_ficar_abaixo_de_inscritos(self):
        c = self.criar()
        a, b = list(c.categorias.all())
        self.inscrever(a)
        self.inscrever(a, self.bruno)
        resposta = self.client.patch(self.detalhe(c), {'categorias': [
            {'id': a.pk, 'nome': a.nome, 'vagas': 1}, {'id': b.pk, 'nome': b.nome}]}, format='json')
        self.assertEqual(resposta.status_code, 400)
        a.refresh_from_db()
        self.assertEqual(a.vagas, 2)

    def test_remover_categoria_sem_vinculos(self):
        c = self.criar()
        a = c.categorias.first()
        resposta = self.client.patch(self.detalhe(c), {'categorias': [{'id': a.pk, 'nome': a.nome}]}, format='json')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(c.categorias.count(), 1)

    def test_antecipar_abertura_encerramento_sem_regressao(self):
        c = self.criar()
        resposta = self.client.patch(self.detalhe(c), {'status': 'inscricoes_abertas'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        c.refresh_from_db()
        self.assertEqual(c.abertura_inscricoes, AGORA)
        with patch('django.utils.timezone.now', return_value=AGORA+timedelta(minutes=1)):
            resposta = self.client.patch(self.detalhe(c), {'status': 'inscricoes_encerradas'}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        c.refresh_from_db()
        self.assertEqual(c.encerramento_inscricoes, AGORA+timedelta(minutes=1))
        self.assertEqual(self.client.patch(self.detalhe(c), {'status': 'planejado'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.detalhe(c), {'status': 'cancelado'}, format='json').status_code, 400)

    def test_cancelamento_motivo_historico_e_email_unico(self):
        c = self.criar()
        for categoria in c.categorias.all():
            self.inscrever(categoria)
        url = self.detalhe(c)+'cancelar/'
        self.assertEqual(self.client.post(url, {'motivo': 'curto'}, format='json').status_code, 400)
        with patch('competicoes.servicos.enviar_email') as enviar:
            with self.captureOnCommitCallbacks(execute=True):
                resposta = self.client.post(url, {'motivo': 'Ginásio indisponível'}, format='json')
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(enviar.call_count, 1)
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(url, {'motivo': 'Ginásio indisponível'}, format='json')
            self.assertEqual(enviar.call_count, 1)
        self.assertEqual(Auditoria.objects.get().justificativa, 'Ginásio indisponível')
        self.assertEqual(c.categorias.count(), 2)
        self.assertEqual(Inscricao.objects.count(), 2)

    def test_cancelamento_finalizado_bloqueado(self):
        c = self.criar()
        Campeonato.objects.filter(pk=c.pk).update(status='finalizado')
        resposta = self.client.post(self.detalhe(c)+'cancelar/', {'motivo': 'Ginásio indisponível'}, format='json')
        self.assertEqual(resposta.status_code, 409)

    def test_editar_local_notifica_apos_commit_sem_duplicar(self):
        c = self.criar()
        for categoria in c.categorias.all():
            self.inscrever(categoria)
        with patch('competicoes.servicos.enviar_email') as enviar:
            with self.captureOnCommitCallbacks(execute=True):
                resposta = self.client.patch(self.detalhe(c), {'local_campeonato': 'Novo ginásio'}, format='json')
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(enviar.call_count, 1)
            with self.captureOnCommitCallbacks(execute=True):
                self.client.patch(self.detalhe(c), {'observacoes': 'Raquetes'}, format='json')
            self.assertEqual(enviar.call_count, 1)

    def test_sincronizacao_limites_e_idempotencia(self):
        c = self.criar()
        self.assertEqual(sincronizar_status(c.abertura_inscricoes-timedelta(seconds=1)), 0)
        self.assertEqual(sincronizar_status(c.abertura_inscricoes), 1)
        self.assertEqual(sincronizar_status(c.abertura_inscricoes), 0)
        self.assertEqual(sincronizar_status(c.encerramento_inscricoes), 1)
        self.assertEqual(sincronizar_status(datetime(2026, 12, 7, 2, 59, tzinfo=tz.utc)), 0)
        self.assertEqual(sincronizar_status(datetime(2026, 12, 7, 3, tzinfo=tz.utc)), 1)
        self.assertEqual(sincronizar_status(datetime(2026, 12, 8, tzinfo=tz.utc)), 0)
        self.assertEqual(Notificacao.objects.filter(tipo='campeonato_finalizado').count(), 1)

    def test_recuperacao_etapas_atrasadas_e_cancelado_preservado(self):
        c = self.criar()
        futuro = datetime(2027, 1, 1, tzinfo=tz.utc)
        self.assertEqual(sincronizar_status(futuro), 1)
        c.refresh_from_db()
        self.assertEqual(c.status, 'finalizado')
        self.assertFalse(Notificacao.objects.filter(tipo='inscricoes_abertas').exists())
        Campeonato.objects.filter(pk=c.pk).update(status='cancelado')
        self.assertEqual(sincronizar_status(futuro), 0)

    def test_listagem_sem_n_mais_um(self):
        self.criar()
        self.criar(nome='Outra Copa')
        with self.assertNumQueries(2):
            dados = CampeonatoSerializer(campeonatos_para(self.ana), many=True).data
        self.assertEqual(len(dados), 2)

    def test_404_e_metodos_fora_do_contrato(self):
        self.assertEqual(self.client.get('/api/v1/campeonatos/99999/').status_code, 404)
        c = self.criar()
        self.assertEqual(self.client.delete(self.detalhe(c)).status_code, 405)
        self.assertEqual(self.client.put(self.detalhe(c), self.payload(), format='json').status_code, 405)

    def test_falha_na_criacao_reverte_campeonato_categorias_e_aviso(self):
        with patch('competicoes.servicos.Categoria.objects.create', side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/v1/campeonatos/', self.payload(), format='json')
        self.assertEqual(Campeonato.objects.count(), 0)
        self.assertEqual(Categoria.objects.count(), 0)
        self.assertEqual(Aviso.objects.count(), 0)

    def test_categoria_com_partida_ou_inscricao_cancelada_preserva_historico(self):
        c = self.criar()
        categoria = c.categorias.get(nome='Feminino')
        inscricao = self.inscrever(categoria, status='cancelada')
        dados = {'categorias': [{'nome': 'Duplas'}]}
        self.assertEqual(self.client.patch(self.detalhe(c), dados, format='json').status_code, 409)
        inscricao.delete()
        Partida.objects.create(atleta=self.ana, adversario=self.bruno, tipo_adversario='poli',
            formato=3, data_jogo=AGORA.date(), status='pendente', campeonato=c, categoria=categoria)
        self.assertEqual(self.client.patch(self.detalhe(c), dados, format='json').status_code, 409)
        self.assertTrue(Categoria.objects.filter(pk=categoria.pk).exists())

    def test_falha_notificacao_nao_deixa_transicao_parcial(self):
        c = self.criar()
        with patch('competicoes.servicos.notificar', side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                sincronizar_status(c.abertura_inscricoes)
        c.refresh_from_db()
        self.assertEqual(c.status, 'planejado')
        self.assertEqual(Notificacao.objects.count(), 0)
        self.assertEqual(sincronizar_status(c.abertura_inscricoes), 1)
        self.assertEqual(sincronizar_status(c.abertura_inscricoes), 0)

    def test_requisicao_sem_permissao_nao_sincroniza(self):
        c = self.criar()
        Campeonato.objects.filter(pk=c.pk).update(abertura_inscricoes=AGORA)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/campeonatos/').status_code, 401)
        c.refresh_from_db()
        self.assertEqual(c.status, 'planejado')
