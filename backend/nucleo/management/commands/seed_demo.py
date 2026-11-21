"""
python manage.py seed_demo [--reset]

Popula o banco com dados de demonstração. Cada app pode ter um arquivo seed.py com a função
seed(rng, ctx); o comando chama todos na ordem abaixo e ignora os apps que ainda não têm seed.
"""
import importlib
import random

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# A ordem importa: partidas usa os campeonatos; tudo usa os usuários.
ORDEM = ["contas", "competicoes", "partidas", "avisos", "calendario"]

# Tabelas apagadas pelo --reset, dos "filhos" para os "pais" (os cursos ficam).
TABELAS_RESET = [
    "nucleo.Auditoria", "nucleo.Notificacao", "nucleo.ExecucaoRotina",
    "partidas.HistoricoPartida", "partidas.SetPartida", "partidas.Contestacao",
    "partidas.Partida", "partidas.AdversarioExterno",
    "calendario.Presenca", "calendario.Evento",
    "avisos.AvisoLeitura", "avisos.Aviso",
    "competicoes.Inscricao", "competicoes.Categoria", "competicoes.Campeonato",
    "authtoken.Token",
]


class Command(BaseCommand):
    help = "Cria os dados de demonstração do PingPoli (usuários, campeonatos, partidas, avisos, eventos)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Apaga os dados atuais antes de criar.")

    @transaction.atomic
    def handle(self, *args, **opcoes):
        Atleta = get_user_model()
        if Atleta.objects.exists():
            if not opcoes["reset"]:
                raise CommandError("O banco já tem dados. Use: python manage.py seed_demo --reset")
            for rotulo in TABELAS_RESET:
                apps.get_model(rotulo).objects.all().delete()
            Atleta.objects.all().delete()
            self.stdout.write("Dados anteriores apagados.")

        rng = random.Random(42)  # mesmo resultado em qualquer computador
        ctx = {}
        for app in ORDEM:
            try:
                modulo = importlib.import_module(f"{app}.seed")
            except ModuleNotFoundError as e:
                if e.name == f"{app}.seed":
                    self.stdout.write(f"  {app}: sem seed.py (ignorado)")
                    continue
                raise
            resumo = modulo.seed(rng, ctx)
            self.stdout.write(f"  {app}: {resumo or 'ok'}")

        self.stdout.write(self.style.SUCCESS("Dados de demonstração criados."))