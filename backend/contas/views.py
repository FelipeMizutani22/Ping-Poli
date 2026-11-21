"""Autenticação (UC01) e lista de cursos (UC02)."""
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.core.validators import validate_email
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Atleta, Curso
from .serializers import AtletaMeSerializer, AtletaResumoSerializer, CursoSerializer

MENSAGENS_SITUACAO = {
    Atleta.Situacao.PENDENTE: ("conta_pendente", "Sua solicitação de cadastro aguarda aprovação da Diretoria"),
    Atleta.Situacao.RECUSADA: (
        "conta_recusada",
        "Sua solicitação não foi aprovada. Procure a Diretoria ou envie nova solicitação",
    ),
    Atleta.Situacao.INATIVA: ("conta_inativa", "Conta desativada. Procure a Diretoria da equipe"),
}


def erro(status_http, codigo, mensagem):
    return Response({"detail": mensagem, "codigo": codigo}, status=status_http)


class LoginView(APIView):
    """POST auth/login/ {email, senha} → {token, atleta}."""

    permission_classes = [AllowAny]
    authentication_classes = []  # login não exige (nem usa) sessão ou token

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        senha = request.data.get("senha") or ""

        # 1. Campos preenchidos e formato do e-mail (UC01 e, f)
        if not email or not senha:
            return erro(status.HTTP_400_BAD_REQUEST, "campos_obrigatorios", "Preencha e-mail e senha")
        try:
            validate_email(email)
        except ValidationError:
            return erro(status.HTTP_400_BAD_REQUEST, "email_invalido", "Formato de e-mail inválido")

        # 2. Credenciais (UC01 g): mesma mensagem exista ou não o e-mail
        atleta = Atleta.objects.filter(email=email).first()
        if atleta is None or not atleta.check_password(senha):
            if atleta is not None:
                atleta.tentativas_login += 1
                atleta.save(update_fields=["tentativas_login"])
            return erro(status.HTTP_401_UNAUTHORIZED, "credenciais_invalidas", "E-mail ou senha incorretos")

        # 3. Situação da conta, revelada só depois da senha certa (UC01 j, k, l)
        if atleta.situacao in MENSAGENS_SITUACAO:
            codigo, mensagem = MENSAGENS_SITUACAO[atleta.situacao]
            return erro(status.HTTP_403_FORBIDDEN, codigo, mensagem)

        # 4. Sucesso: zera tentativas, registra o acesso e devolve o token (UC01 passo 8)
        atleta.tentativas_login = 0
        atleta.last_login = timezone.now()
        atleta.save(update_fields=["tentativas_login", "last_login"])
        token, _ = Token.objects.get_or_create(user=atleta)
        return Response({"token": token.key, "atleta": AtletaMeSerializer(atleta).data})


class LogoutView(APIView):
    """POST auth/logout/ → apaga o token (o usuário precisa logar de novo)."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    """GET auth/me/ → dados do usuário logado."""

    serializer_class = AtletaMeSerializer

    def get_object(self):
        return self.request.user


class CursoListView(generics.ListAPIView):
    """GET cursos/ → lista pública (usada no formulário de cadastro)."""

    permission_classes = [AllowAny]
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer



class AtletaOpcoesView(generics.ListAPIView):
    """
    GET atletas/opcoes/?q=ana&incluir_inativos=1
    Busca atletas por nome ou NUSP para campos de seleção (partida, presença, confronto).
    Devolve no máximo 20, sem o próprio usuário. Inativos só com incluir_inativos=1 (UC19).
    """

    serializer_class = AtletaResumoSerializer
    pagination_class = None
    LIMITE = 20

    def get_queryset(self):
        situacoes = [Atleta.Situacao.ATIVA]
        if self.request.query_params.get("incluir_inativos") == "1":
            situacoes.append(Atleta.Situacao.INATIVA)
        qs = Atleta.objects.filter(situacao__in=situacoes).exclude(pk=self.request.user.pk)

        termo = (self.request.query_params.get("q") or "").strip()
        if termo:
            filtro = Q(nome__icontains=termo)
            if termo.isdigit():
                filtro |= Q(nusp=int(termo))
            qs = qs.filter(filtro)
        return qs.order_by("nome")[: self.LIMITE]