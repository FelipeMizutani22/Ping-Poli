"""
Permissões da API do PingPoli.
- AtletaAtivo: usuário autenticado com conta Ativa (padrão de todas as rotas).
- Diretor: AtletaAtivo + perfil Diretor de Modalidade.
"""
from rest_framework.permissions import BasePermission


class AtletaAtivo(BasePermission):
    message = "Sua conta não está ativa. Procure a Diretoria da equipe."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.situacao == "ativa")


class Diretor(AtletaAtivo):
    message = "Apenas o Diretor de Modalidade pode realizar esta ação."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.papel == "diretor"