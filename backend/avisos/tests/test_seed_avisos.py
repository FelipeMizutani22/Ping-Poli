"""Testes dos avisos de demonstração (C4 · 08_DEMO_E_ENTREGA §1)."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from avisos.models import Aviso, AvisoLeitura


class SeedAvisosTests(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=StringIO())

    def test_seis_avisos_dois_fixados_um_urgente(self):
        self.assertEqual(Aviso.objects.count(), 6)
        fixados = Aviso.objects.filter(fixado=True)
        self.assertEqual(fixados.count(), 2)
        self.assertTrue(fixados.filter(categoria="urgente").exists())

    def test_um_expirado(self):
        self.assertEqual(Aviso.objects.filter(data_expiracao__lt=timezone.localdate()).count(), 1)

    def test_ana_leu_metade(self):
        lidos = AvisoLeitura.objects.filter(atleta__email="ana.lima@usp.br")
        self.assertEqual(lidos.count(), 3)
        self.assertFalse(lidos.filter(aviso__fixado=True).exists())   # os fixados aparecem como "Novo"
