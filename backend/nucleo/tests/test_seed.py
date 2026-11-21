from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class SeedDemoTests(TestCase):
    def rodar(self, *args):
        call_command("seed_demo", *args, stdout=StringIO())

    def test_cria_os_usuarios_de_teste(self):
        self.rodar()
        Atleta = get_user_model()
        self.assertEqual(Atleta.objects.count(), 13)
        marina = Atleta.objects.get(email="marina.souza@usp.br")
        self.assertTrue(marina.is_superuser and marina.eh_diretor)
        self.assertTrue(marina.check_password("pingpoli123"))
        self.assertEqual(Atleta.objects.get(email="julia.martins@usp.br").situacao, "pendente")

    def test_sem_reset_recusa_banco_com_dados(self):
        self.rodar()
        with self.assertRaises(CommandError):
            self.rodar()

    def test_reset_pode_rodar_varias_vezes(self):
        self.rodar()
        self.rodar("--reset")
        self.rodar("--reset")
        self.assertEqual(get_user_model().objects.count(), 13)