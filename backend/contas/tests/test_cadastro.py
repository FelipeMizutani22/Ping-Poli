"""Testes da solicitação de cadastro (UC02)."""
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework.test import APITestCase

from contas.models import Curso
from nucleo.models import Notificacao

URL = "/api/v1/cadastro/"
Atleta = get_user_model()


class CadastroTests(APITestCase):
    def setUp(self):
        self.curso = Curso.objects.first()
        self.marina = Atleta.objects.create_superuser(
            "marina@usp.br", "pingpoli123", nome="Marina Souza", nusp=1, curso=self.curso, ano_ingresso=2022
        )

    def dados(self, **troca):
        base = {
            "nome": "João da Silva", "nusp": 15500099, "email": "Joao.Silva@usp.br", "curso": self.curso.id,
            "ano_ingresso": timezone.localdate().year - 1, "telefone": "(11) 98888-7777",
            "senha": "senhaforte1", "senha_confirmacao": "senhaforte1", "aceite_termos": True,
        }
        base.update(troca)
        return base

    def enviar(self, **troca):
        return self.client.post(URL, self.dados(**troca), format="json")

    def test_cadastro_valido_cria_conta_pendente_e_avisa_diretoria(self):
        r = self.enviar()
        self.assertEqual(r.status_code, 201)
        self.assertIn("Solicitação enviada!", r.data["detail"])
        joao = Atleta.objects.get(nusp=15500099)
        self.assertEqual((joao.email, joao.situacao, joao.papel), ("joao.silva@usp.br", "pendente", "atleta"))
        self.assertTrue(joao.check_password("senhaforte1"))
        self.assertTrue(Notificacao.objects.filter(destinatario=self.marina, tipo="cadastro_pendente").exists())
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["joao.silva@usp.br", "marina@usp.br"])

    def test_validacoes_por_campo(self):
        casos = {
            "nome": "J0ão",
            "email": "joao@gmail.com",
            "ano_ingresso": 1990,
            "telefone": "11988887777",
            "senha": "curta",
            "aceite_termos": False,
            "curso": 9999,
        }
        for campo, valor in casos.items():
            with self.subTest(campo=campo):
                r = self.enviar(**{campo: valor})
                self.assertEqual(r.status_code, 400)
                self.assertIn(campo, r.data)
        self.assertEqual(Atleta.objects.count(), 1)  # nada foi gravado

    def test_confirmacao_de_senha_diferente(self):
        r = self.enviar(senha_confirmacao="outrasenha")
        self.assertEqual(r.status_code, 400)
        self.assertIn("senha_confirmacao", r.data)

    def test_email_ou_nusp_de_conta_ativa(self):
        r = self.enviar(email="marina@usp.br")
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "conta_existente"))
        r = self.enviar(nusp=1)
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "conta_existente"))

    def test_solicitacao_ja_pendente(self):
        self.enviar()
        r = self.enviar()
        self.assertEqual((r.status_code, r.data["codigo"]), (409, "solicitacao_pendente"))

    def test_nova_solicitacao_apos_recusa_reaproveita_a_conta(self):
        self.enviar()
        joao = Atleta.objects.get(nusp=15500099)
        joao.situacao = "recusada"
        joao.motivo_recusa = "Dados incompletos"
        joao.save()
        r = self.enviar(nome="João Pedro da Silva")
        self.assertEqual(r.status_code, 201)
        joao.refresh_from_db()
        self.assertEqual((joao.situacao, joao.nome, joao.motivo_recusa), ("pendente", "João Pedro da Silva", ""))
        self.assertEqual(Atleta.objects.filter(nusp=15500099).count(), 1)