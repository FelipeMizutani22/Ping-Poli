from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from contas.models import Curso


class AtletaModeloTests(TestCase):
    def setUp(self):
        self.curso = Curso.objects.get(nome="Engenharia Mecatrônica")  # criado pela migração 0002

    def test_cursos_carregados_pela_migracao(self):
        self.assertEqual(Curso.objects.count(), 13)

    def test_create_user_padroes_e_email_minusculo(self):
        a = get_user_model().objects.create_user(
            "Ana.Lima@USP.br", "pingpoli123", nome="Ana Lima", nusp=111, curso=self.curso, ano_ingresso=2024
        )
        self.assertEqual(a.email, "ana.lima@usp.br")
        self.assertEqual(a.papel, "atleta")
        self.assertEqual(a.situacao, "pendente")
        self.assertTrue(a.check_password("pingpoli123"))
        self.assertFalse(a.is_staff)

    def test_create_superuser_vira_diretor_ativo(self):
        m = get_user_model().objects.create_superuser(
            "marina.souza@usp.br", "pingpoli123", nome="Marina Souza", nusp=222, curso=self.curso, ano_ingresso=2022
        )
        self.assertTrue(m.eh_diretor and m.is_staff and m.is_superuser)
        self.assertEqual(m.situacao, "ativa")

    def test_colunas_do_er(self):
        with connection.cursor() as c:
            colunas = [col.name for col in connection.introspection.get_table_description(c, "atleta")]
        self.assertIn("senha_hash", colunas)
        self.assertIn("ultimo_acesso", colunas)