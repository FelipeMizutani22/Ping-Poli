from rest_framework import serializers

from .models import Atleta, Curso


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ["id", "nome"]


class AtletaMeSerializer(serializers.ModelSerializer):
    """Dados do próprio usuário logado (resposta do login e de auth/me/)."""

    curso = CursoSerializer(read_only=True)
    ultimo_acesso = serializers.DateTimeField(source="last_login", read_only=True)

    class Meta:
        model = Atleta
        fields = [
            "id", "nome", "nusp", "email", "curso", "ano_ingresso", "telefone", "foto",
            "mao_dominante", "papel", "situacao", "ultimo_acesso",
        ]



class AtletaResumoSerializer(serializers.ModelSerializer):
    """Formato curto, usado em buscas e listas (ex.: escolher o adversário de uma partida)."""

    class Meta:
        model = Atleta
        fields = ["id", "nome", "nusp"]