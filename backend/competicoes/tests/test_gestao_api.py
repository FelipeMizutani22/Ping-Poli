import json
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from contas.models import Curso
from competicoes.models import Campeonato, Categoria, Inscricao
from nucleo.models import Auditoria, Notificacao


class GestaoInscricoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def usuario(nome, nusp, papel='atleta', situacao='ativa'):
            return get_user_model().objects.create_user(email=f'{nome}@usp.br', password='senha123', nome=nome, nusp=nusp, curso=Curso.objects.first(), ano_ingresso=2024, papel=papel, situacao=situacao)
        cls.d = usuario('Diretor', 101, 'diretor')
        cls.a = usuario('Ana', 102)
        cls.b = usuario('Bruno', 103)
        cls.inativo = usuario('Inativo', 104, situacao='inativa')

    def setUp(self):
        agora = timezone.now()
        self.c = Campeonato.objects.create(nome='Copa', organizador='Poli', local_campeonato='USP', data_inicio=timezone.localdate()-timedelta(days=2), data_fim=timezone.localdate()-timedelta(days=1), abertura_inscricoes=agora-timedelta(days=10), encerramento_inscricoes=agora-timedelta(days=3), status='finalizado', criado_por=self.d)
        self.cat = Categoria.objects.create(campeonato=self.c, nome='Livre', vagas=3)
        self.cat2 = Categoria.objects.create(campeonato=self.c, nome='Outra', vagas=None)
        self.i = Inscricao.objects.create(categoria=self.cat, atleta=self.a, inscrito_por=self.a, observacoes='Observação')
        self.j = Inscricao.objects.create(categoria=self.cat, atleta=self.b, inscrito_por=self.b)
        self.client = APIClient(); self.client.force_authenticate(self.d)
        self.url = f'/api/v1/campeonatos/{self.c.pk}/inscricoes/'
        self.resultados = f'/api/v1/campeonatos/{self.c.pk}/resultados/'

    def salvar(self, itens, **extra):
        return self.client.patch(self.resultados, {'resultados': itens, **extra}, format='json')

    def test_lista_agrupada_vagas_dados_e_sem_cancelados(self):
        Inscricao.objects.create(categoria=self.cat2, atleta=self.a, inscrito_por=self.d, status='cancelada')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        grupos = {c['id']: c for c in r.data['categorias']}
        self.assertEqual(grupos[self.cat.pk]['total_inscritos'], 2)
        self.assertEqual(grupos[self.cat.pk]['vagas_restantes'], 1)
        self.assertEqual(grupos[self.cat2.pk]['inscricoes'], [])
        self.assertIsNone(grupos[self.cat2.pk]['vagas_restantes'])
        self.assertEqual(grupos[self.cat.pk]['inscricoes'][0]['atleta']['nome'], 'Ana')
        self.assertEqual(grupos[self.cat.pk]['inscricoes'][0]['observacoes'], 'Observação')

    def test_permissoes_em_todas_rotas(self):
        for user, codigo in [(None, 401), (self.a, 403), (self.inativo, 403)]:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(self.url).status_code, codigo)
            self.assertEqual(self.client.post(self.url, {}, format='json').status_code, codigo)
            self.assertEqual(self.salvar([]).status_code, codigo)
            self.assertEqual(self.client.patch(f'/api/v1/inscricoes/{self.i.pk}/resultado/', {}, format='json').status_code, codigo)
            self.assertEqual(self.client.post(f'/api/v1/inscricoes/{self.i.pk}/remover/', {}, format='json').status_code, codigo)

    def test_resultados_auditoria_e_dashboard(self):
        r = self.salvar([{'id': self.i.pk, 'colocacao': 1, 'destaque': 'Campeã'}, {'id': self.j.pk, 'colocacao': 2}])
        self.assertEqual(r.status_code, 200, r.data)
        log = Auditoria.objects.get(registro_id=self.i.pk, acao='registrar_resultado')
        self.assertEqual(log.autor, self.d)
        self.assertIsNotNone(log.data_acao)
        self.assertEqual(json.loads(log.valor_anterior)['colocacao'], None)
        self.assertEqual(json.loads(log.valor_novo)['colocacao'], 1)
        self.client.force_authenticate(self.a)
        r = self.client.get('/api/v1/desempenho/', {'periodo': 'custom', 'inicio': self.c.data_inicio.isoformat(), 'fim': self.c.data_fim.isoformat()})
        self.assertEqual(r.data['colocacoes'][0]['colocacao'], 1)
        self.assertEqual(r.data['colocacoes'][0]['destaque'], 'Campeã')

    def test_patch_individual_e_limpeza(self):
        url = f'/api/v1/inscricoes/{self.i.pk}/resultado/'
        self.assertEqual(self.client.patch(url, {'colocacao': 3, 'destaque': 'Bronze'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'destaque': ''}, format='json').data['colocacao'], 3)
        self.assertEqual(self.client.patch(url, {'colocacao': None}, format='json').data['colocacao'], None)
        self.assertEqual(Auditoria.objects.filter(acao='registrar_resultado').count(), 3)

    def test_empate_exige_confirmacao_sem_gravacao_parcial(self):
        itens = [{'id': self.i.pk, 'colocacao': 1}, {'id': self.j.pk, 'colocacao': 1}]
        r = self.salvar(itens)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['codigo'], 'confirmar_empate')
        self.i.refresh_from_db(); self.assertIsNone(self.i.colocacao)
        self.assertEqual(Auditoria.objects.count(), 0)
        self.assertEqual(self.salvar(itens, confirmar_empate=True).status_code, 200)
        self.assertEqual(Inscricao.objects.filter(colocacao=1).count(), 2)

    def test_empate_com_inscricao_fora_do_lote(self):
        self.j.colocacao = 2; self.j.save()
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 2}]).status_code, 409)

    def test_troca_de_posicoes_lote_nao_cria_falso_empate(self):
        self.i.colocacao = 1; self.i.save(); self.j.colocacao = 2; self.j.save()
        r = self.salvar([{'id': self.i.pk, 'colocacao': 2}, {'id': self.j.pk, 'colocacao': 1}])
        self.assertEqual(r.status_code, 200)

    def test_colocacao_igual_em_categorias_distintas(self):
        outra = Inscricao.objects.create(categoria=self.cat2, atleta=self.a, inscrito_por=self.a)
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 1}, {'id': outra.pk, 'colocacao': 1}]).status_code, 200)

    def test_datas_status_e_cancelamento_inscricao(self):
        self.c.data_inicio = timezone.localdate()+timedelta(days=1)
        self.c.data_fim = self.c.data_inicio; self.c.save()
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 1}]).status_code, 409)
        self.assertFalse(self.client.get(self.url).data['pode_registrar_resultados'])
        self.c.data_inicio = timezone.localdate(); self.c.save()
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 1}]).status_code, 200)
        self.c.status = 'cancelado'; self.c.save()
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 2}]).status_code, 409)
        self.c.status = 'finalizado'; self.c.save()
        self.i.status = 'cancelada'; self.i.save()
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 2}]).status_code, 400)

    def test_validacao_e_rollback(self):
        for valor in (0, -1, 1.5, 32768, 'abc'):
            self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': valor}]).status_code, 400)
        self.assertEqual(self.salvar([{'id': self.i.pk, 'destaque': 'x'*51}]).status_code, 400)
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 1}, {'id': self.j.pk, 'colocacao': 0}]).status_code, 400)
        self.i.refresh_from_db(); self.assertIsNone(self.i.colocacao)
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 1}, {'id': self.i.pk, 'colocacao': 2}]).status_code, 400)
        self.assertEqual(self.salvar([{'id': 99999, 'colocacao': 1}]).status_code, 400)

    def test_inscricao_de_outro_campeonato(self):
        self.c.pk = None; self.c.nome = 'Outra Copa'; self.c.save()
        cat = Categoria.objects.create(campeonato=self.c, nome='Outra Copa')
        i = Inscricao.objects.create(categoria=cat, atleta=self.a, inscrito_por=self.a)
        self.assertEqual(self.salvar([{'id': self.i.pk, 'colocacao': 1}, {'id': i.pk, 'colocacao': 1}]).status_code, 400)
        self.i.refresh_from_db(); self.assertIsNone(self.i.colocacao)

    def test_inclusao_fora_do_prazo_autor_e_notificacao(self):
        with patch('competicoes.gestao.enviar_email') as email, self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(self.url, {'atleta': self.b.pk, 'categorias': [self.cat2.pk]}, format='json')
            self.assertEqual(r.status_code, 201, r.data)
            email.assert_not_called()
        email.assert_called_once()
        self.assertEqual(Inscricao.objects.get(atleta=self.b, categoria=self.cat2).inscrito_por, self.d)
        self.assertTrue(Notificacao.objects.filter(destinatario=self.b).exists())

    def test_manual_duplicada_lotada_inativa_e_cancelado(self):
        r = self.client.post(self.url, {'atleta': self.a.pk, 'categorias': [self.cat.pk, self.cat2.pk]}, format='json')
        self.assertEqual(r.data['codigo'], 'ja_inscrito')
        self.assertFalse(Inscricao.objects.filter(categoria=self.cat2).exists())
        self.cat.vagas = 2; self.cat.save()
        r = self.client.post(self.url, {'atleta': self.d.pk, 'categorias': [self.cat.pk, self.cat2.pk]}, format='json')
        self.assertEqual(r.data['codigo'], 'sem_vagas')
        self.assertFalse(Inscricao.objects.filter(categoria=self.cat2).exists())
        self.assertEqual(self.client.post(self.url, {'atleta': self.inativo.pk, 'categorias': [self.cat2.pk]}, format='json').status_code, 404)
        self.c.status = 'cancelado'; self.c.save()
        self.assertEqual(self.client.post(self.url, {'atleta': self.d.pk, 'categorias': [self.cat2.pk]}, format='json').status_code, 409)

    def test_remover_motivo_auditoria_vaga_reinscricao(self):
        url = f'/api/v1/inscricoes/{self.i.pk}/remover/'
        self.assertEqual(self.client.post(url, {'motivo': 'curto'}, format='json').status_code, 400)
        with patch('competicoes.gestao.enviar_email') as email, self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(url, {'motivo': 'Atleta solicitou retirada'}, format='json').status_code, 204)
            self.assertEqual(self.client.post(url, {'motivo': 'Atleta solicitou retirada'}, format='json').status_code, 204)
        email.assert_called_once()
        self.i.refresh_from_db(); self.assertEqual(self.i.status, 'cancelada')
        self.assertEqual(Auditoria.objects.get(acao='remover_manualmente').justificativa, 'Atleta solicitou retirada')
        self.assertEqual(self.client.post(self.url, {'atleta': self.a.pk, 'categorias': [self.cat.pk]}, format='json').status_code, 201)
        self.assertEqual(Inscricao.objects.filter(atleta=self.a, categoria=self.cat).count(), 1)
        self.i.refresh_from_db(); self.assertEqual(self.i.status, 'ativa')

    def test_falha_de_auditoria_reverte_todo_lote(self):
        with patch('competicoes.gestao.auditar', side_effect=[None, RuntimeError('falha simulada')]):
            with self.assertRaises(RuntimeError):
                self.salvar([{'id': self.i.pk, 'colocacao': 1}, {'id': self.j.pk, 'colocacao': 2}])
        self.i.refresh_from_db(); self.j.refresh_from_db()
        self.assertIsNone(self.i.colocacao)
        self.assertIsNone(self.j.colocacao)
