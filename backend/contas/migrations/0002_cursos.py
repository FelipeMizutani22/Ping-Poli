"""Carrega a lista de cursos de graduação da Escola Politécnica."""
from django.db import migrations

CURSOS = [
    "Engenharia Ambiental",
    "Engenharia Civil",
    "Engenharia de Computação",
    "Engenharia Elétrica",
    "Engenharia de Materiais",
    "Engenharia Mecânica",
    "Engenharia Mecatrônica",
    "Engenharia Metalúrgica",
    "Engenharia de Minas",
    "Engenharia Naval",
    "Engenharia de Petróleo",
    "Engenharia de Produção",
    "Engenharia Química",
]


def criar_cursos(apps, schema_editor):
    Curso = apps.get_model("contas", "Curso")
    for nome in CURSOS:
        Curso.objects.get_or_create(nome=nome)


def remover_cursos(apps, schema_editor):
    apps.get_model("contas", "Curso").objects.filter(nome__in=CURSOS).delete()


class Migration(migrations.Migration):
    dependencies = [("contas", "0001_initial")]
    operations = [migrations.RunPython(criar_cursos, remover_cursos)]