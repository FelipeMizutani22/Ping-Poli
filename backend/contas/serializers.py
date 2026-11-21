from rest_framework import serializers
from django.utils import timezone

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



class SolicitacaoCadastroSerializer(serializers.Serializer):
    """Valida o formulário de solicitação de cadastro (UC02). Só validação: quem grava é o serviço."""

    nome = serializers.RegexField(
        r"^[A-Za-zÀ-ÖØ-öø-ÿ ]{3,100}$",
        error_messages={"invalid": "Use apenas letras e espaços (3 a 100 caracteres)."},
    )
    nusp = serializers.IntegerField(min_value=1, error_messages={"invalid": "O NUSP deve conter apenas números."})
    email = serializers.EmailField(max_length=100, error_messages={"invalid": "Formato de e-mail inválido."})
    curso = serializers.PrimaryKeyRelatedField(
        queryset=Curso.objects.all(), error_messages={"does_not_exist": "Selecione um curso válido."}
    )
    ano_ingresso = serializers.IntegerField()
    telefone = serializers.RegexField(
        r"^\(\d{2}\) \d{5}-\d{4}$", required=False, allow_blank=True,
        error_messages={"invalid": "Use o formato (99) 99999-9999."},
    )
    senha = serializers.CharField(write_only=True, trim_whitespace=False)
    senha_confirmacao = serializers.CharField(write_only=True, trim_whitespace=False)
    aceite_termos = serializers.BooleanField()

    def validate_nome(self, valor):
        return " ".join(valor.split())  # tira espaços repetidos

    def validate_email(self, valor):
        valor = valor.strip().lower()
        if not valor.endswith("@usp.br"):
            raise serializers.ValidationError("Use o seu e-mail institucional (@usp.br).")
        return valor

    def validate_ano_ingresso(self, valor):
        atual = timezone.localdate().year
        if not atual - 10 <= valor <= atual:
            raise serializers.ValidationError(f"Informe um ano entre {atual - 10} e {atual}.")
        return valor

    def validate_senha(self, valor):
        if not 8 <= len(valor) <= 64:
            raise serializers.ValidationError("A senha deve ter de 8 a 64 caracteres.")
        return valor

    def validate_aceite_termos(self, valor):
        if not valor:
            raise serializers.ValidationError("É preciso aceitar os termos de uso e a política de privacidade.")
        return valor

    def validate(self, dados):
        if dados["senha"] != dados["senha_confirmacao"]:
            raise serializers.ValidationError({"senha_confirmacao": "As senhas não conferem."})
        return dados



class AtletaAdminSerializer(serializers.ModelSerializer):
    """Visão do Diretor na gestão de atletas (UC03)."""

    curso = CursoSerializer(read_only=True)
    ultimo_acesso = serializers.DateTimeField(source="last_login", read_only=True)

    class Meta:
        model = Atleta
        fields = [
            "id", "nome", "nusp", "email", "curso", "ano_ingresso", "telefone", "papel", "situacao",
            "data_solicitacao", "data_avaliacao", "motivo_recusa", "ultimo_acesso",
        ]


class RecusaSerializer(serializers.Serializer):
    motivo = serializers.CharField(
        max_length=300, error_messages={"blank": "Informe o motivo da recusa.", "required": "Informe o motivo da recusa."}
    )



class PapelSerializer(serializers.Serializer):
    papel = serializers.ChoiceField(
        choices=Atleta.Papel.choices, error_messages={"invalid_choice": "Papel inválido. Use 'atleta' ou 'diretor'."}
    )