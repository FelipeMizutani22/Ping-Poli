"""Regras de negócio do app partidas."""
from .models import AdversarioExterno

MSG_ADVERSARIO_JA_EXISTE = "Adversário externo já cadastrado"


class AdversarioJaExiste(Exception):
    """Já existe um adversário externo com o mesmo nome (UC15-j)."""

    def __init__(self, existente):
        super().__init__(MSG_ADVERSARIO_JA_EXISTE)
        self.existente = existente


def cadastrar_adversario_externo(nome, clube=""):
    """
    Cadastra um adversário externo (UC15-a, passo 4).
    Se já existir um com o mesmo nome (sem diferenciar maiúsculas), levanta AdversarioJaExiste.
    """
    existente = AdversarioExterno.objects.filter(nome__iexact=nome).first()
    if existente is not None:
        raise AdversarioJaExiste(existente)
    return AdversarioExterno.objects.create(nome=nome, clube=clube)
