from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from contas.models import Curso
from competicoes.models import Campeonato, Categoria, Inscricao


class InscricoesTests(TestCase):
    def setUp(self):
        def usuario(n):
            return get_user_model().objects.create_user(email=f'{n}@usp.br', password='senha123', nome=n, nusp=101 if n == 'Ana' else 102, ano_ingresso=2024, curso=Curso.objects.first(), situacao='ativa')
        self.ana = usuario('Ana'); self.bruno = usuario('Bruno')
        agora = timezone.now()
        self.c = Campeonato.objects.create(nome='Copa', organizador='Poli', local_campeonato='USP', data_inicio=agora.date()+timedelta(days=3), data_fim=agora.date()+timedelta(days=4), abertura_inscricoes=agora-timedelta(days=1), encerramento_inscricoes=agora+timedelta(days=1), status='inscricoes_abertas', criado_por=self.ana)
        self.a = Categoria.objects.create(campeonato=self.c, nome='A', vagas=1)
        self.b = Categoria.objects.create(campeonato=self.c, nome='B', vagas=None)
        self.client = APIClient(); self.client.force_authenticate(self.ana)

    def inscrever(self, ids=None, **extras):
        return self.client.post('/api/v1/inscricoes/', {'categorias': ids or [self.a.pk, self.b.pk], 'ciencia_regulamento': True, **extras}, format='json')

    def test_multiplas_categorias_email_apos_commit(self):
        with patch('competicoes.inscricoes.enviar_email') as email, self.captureOnCommitCallbacks(execute=True):
            r = self.inscrever()
            self.assertEqual(r.status_code, 201, r.data)
            self.assertEqual(len(r.data), 2)
            email.assert_not_called()
        email.assert_called_once()
        self.assertEqual(Inscricao.objects.filter(status='ativa').count(), 2)

    def test_lotacao_atomica_e_ids_numericos(self):
        Inscricao.objects.create(categoria=self.a, atleta=self.bruno, inscrito_por=self.bruno)
        r = self.inscrever()
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['categorias_esgotadas'], [self.a.pk])
        self.assertFalse(Inscricao.objects.filter(atleta=self.ana).exists())

    def test_duplicada_nao_inscreve_outra_categoria(self):
        self.inscrever([self.a.pk])
        r = self.inscrever()
        self.assertEqual(r.data['codigo'], 'ja_inscrito')
        self.assertFalse(Inscricao.objects.filter(categoria=self.b).exists())

    def test_cancelar_libera_vaga_e_reinscrever_preserva_id(self):
        r = self.inscrever([self.a.pk]); pk = r.data[0]['id']
        self.assertEqual(self.client.delete(f'/api/v1/inscricoes/{pk}/').status_code, 204)
        self.assertEqual(self.inscrever([self.a.pk]).data[0]['id'], pk)
        self.assertEqual(Inscricao.objects.count(), 1)

    def test_cancelamento_repetido_nao_repete_email(self):
        pk = self.inscrever([self.a.pk]).data[0]['id']
        with patch('competicoes.inscricoes.enviar_email') as email, self.captureOnCommitCallbacks(execute=True):
            self.client.delete(f'/api/v1/inscricoes/{pk}/')
            self.client.delete(f'/api/v1/inscricoes/{pk}/')
        email.assert_called_once()

    def test_privacidade(self):
        pk = self.inscrever([self.a.pk]).data[0]['id']
        self.client.force_authenticate(self.bruno)
        self.assertEqual(self.client.get('/api/v1/inscricoes/minhas/').data, [])
        self.assertEqual(self.client.delete(f'/api/v1/inscricoes/{pk}/').status_code, 404)

    def test_prazo_inclusivo_no_encerramento(self):
        pk = self.inscrever([self.a.pk]).data[0]['id']
        with patch('django.utils.timezone.now', return_value=self.c.encerramento_inscricoes):
            self.assertEqual(self.inscrever([self.b.pk]).status_code, 409)
            self.assertEqual(self.client.delete(f'/api/v1/inscricoes/{pk}/').status_code, 409)
        self.assertEqual(Inscricao.objects.get(pk=pk).status, 'ativa')

    def test_campeonato_cancelado(self):
        self.c.status = 'cancelado'; self.c.save()
        self.assertEqual(self.inscrever().status_code, 409)

    def test_validacao(self):
        for payload in [{'categorias': []}, {'categorias': [self.a.pk, self.a.pk]}, {'categorias': [999999]}, {'ciencia_regulamento': False}, {'observacoes': 'x'*301}]:
            dados = {'categorias': [self.a.pk], 'ciencia_regulamento': True, **payload}
            self.assertEqual(self.client.post('/api/v1/inscricoes/', dados, format='json').status_code, 400)
        self.assertFalse(Inscricao.objects.exists())

    def test_autenticacao_e_inativo(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.inscrever().status_code, 401)
        self.ana.situacao = 'inativa'; self.ana.save()
        self.client.force_authenticate(self.ana)
        self.assertEqual(self.inscrever().status_code, 403)
