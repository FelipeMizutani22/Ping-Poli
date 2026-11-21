import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from contas.models import Curso
from nucleo.models import Auditoria, Notificacao
from nucleo.servicos import auditar, enviar_email, notificar, notificar_diretores


def criar(email, nusp, papel="atleta", situacao="ativa"):
    return get_user_model().objects.create_user(
        email, "pingpoli123", nome=email.split("@")[0], nusp=nusp,
        curso=Curso.objects.first(), ano_ingresso=2024, papel=papel, situacao=situacao,
    )


class ServicosTests(TestCase):
    def setUp(self):
        self.ana = criar("ana@usp.br", 1)
        self.marina = criar("marina@usp.br", 2, papel="diretor")
        self.rafael = criar("rafael@usp.br", 3, papel="diretor")
        criar("ex@usp.br", 4, papel="diretor", situacao="inativa")

    def test_notificar(self):
        n = notificar(self.ana, "partida_pendente", "Bruno registrou uma partida", "/partidas/pendentes")
        self.assertFalse(n.lida)
        self.assertEqual(self.ana.notificacoes.count(), 1)

    def test_notificar_diretores_so_ativos_e_com_excecao(self):
        notificar_diretores("cadastro_pendente", "Nova solicitação", exceto=self.rafael)
        destinatarios = list(Notificacao.objects.values_list("destinatario__email", flat=True))
        self.assertEqual(destinatarios, ["marina@usp.br"])

    def test_auditar_guarda_json(self):
        auditar("atleta", self.ana.pk, "aprovar", self.marina, "ok",
                anterior={"situacao": "pendente"}, novo={"situacao": "ativa"})
        reg = Auditoria.objects.get()
        self.assertEqual(json.loads(reg.valor_novo), {"situacao": "ativa"})
        self.assertEqual(reg.valor_anterior and json.loads(reg.valor_anterior)["situacao"], "pendente")

    def test_enviar_email(self):
        self.assertTrue(enviar_email("ana@usp.br", "Cadastro aprovado", "Bem-vinda!"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@usp.br"])