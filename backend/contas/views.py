"""Views do app contas: autenticação (UC01), cadastro (UC02), busca e gestão de atletas (UC03)."""
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Atleta, Curso
from .permissoes import Diretor
from .serializers import (
    AtletaAdminSerializer,
    AtletaMeSerializer,
    AtletaResumoSerializer,
    CursoSerializer,
    PapelSerializer,
    PerfilSerializer,
    RecusaSerializer,
    SolicitacaoCadastroSerializer,
    TrocaSenhaSerializer
)
from .servicos import (
    MSG_SOLICITACAO_ENVIADA,
    ConflitoCadastro,
    SituacaoInvalida,
    UltimoDiretor,
    aprovar_cadastro,
    mudar_papel,
    mudar_situacao,
    recusar_cadastro,
    solicitar_cadastro,
)

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



class CadastroView(APIView):
    """POST cadastro/ → solicitação de cadastro de um Visitante (UC02). A conta nasce Pendente."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SolicitacaoCadastroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 com os erros por campo
        try:
            _, emails_ok = solicitar_cadastro(serializer.validated_data)
        except ConflitoCadastro as conflito:
            return erro(status.HTTP_409_CONFLICT, conflito.codigo, conflito.mensagem)

        resposta = {"detail": MSG_SOLICITACAO_ENVIADA}
        if not emails_ok:  # UC02-h: a conta fica criada mesmo se o e-mail falhar
            resposta["aviso"] = "O e-mail de confirmação pode não chegar."
        return Response(resposta, status=status.HTTP_201_CREATED)



# --- Gestão de atletas pelo Diretor (UC03) ---------------------------------


class Paginacao20(PageNumberPagination):
    page_size = 20


class AtletaListView(generics.ListAPIView):
    """GET atletas/?situacao=pendente&papel=&busca=&page= → lista paginada (Diretor)."""

    permission_classes = [Diretor]
    serializer_class = AtletaAdminSerializer
    pagination_class = Paginacao20

    def get_queryset(self):
        params = self.request.query_params
        qs = Atleta.objects.select_related("curso")
        if params.get("situacao"):
            qs = qs.filter(situacao=params["situacao"])
        if params.get("papel"):
            qs = qs.filter(papel=params["papel"])
        busca = (params.get("busca") or "").strip()
        if busca:
            filtro = Q(nome__icontains=busca)
            if busca.isdigit():
                filtro |= Q(nusp=int(busca))
            qs = qs.filter(filtro)
        # Solicitações pendentes: da mais antiga para a mais recente (UC03)
        if params.get("situacao") == Atleta.Situacao.PENDENTE:
            return qs.order_by("data_solicitacao")
        return qs.order_by("nome")


class AtletaDetailView(generics.RetrieveAPIView):
    """GET atletas/{id}/ → dados completos (Diretor)."""

    permission_classes = [Diretor]
    serializer_class = AtletaAdminSerializer
    queryset = Atleta.objects.select_related("curso")


class AprovarView(APIView):
    """POST atletas/{id}/aprovar/"""

    permission_classes = [Diretor]

    def post(self, request, pk):
        get_object_or_404(Atleta, pk=pk)
        try:
            atleta = aprovar_cadastro(pk, request.user)
        except SituacaoInvalida as e:
            return erro(status.HTTP_409_CONFLICT, "situacao_invalida", str(e))
        return Response(AtletaAdminSerializer(atleta).data)


class RecusarView(APIView):
    """POST atletas/{id}/recusar/ {motivo}"""

    permission_classes = [Diretor]

    def post(self, request, pk):
        get_object_or_404(Atleta, pk=pk)
        dados = RecusaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        try:
            atleta = recusar_cadastro(pk, request.user, dados.validated_data["motivo"])
        except SituacaoInvalida as e:
            return erro(status.HTTP_409_CONFLICT, "situacao_invalida", str(e))
        return Response(AtletaAdminSerializer(atleta).data)



class MudarSituacaoView(APIView):
    """POST atletas/{id}/inativar/ ou atletas/{id}/reativar/ (a URL define a nova situação)."""

    permission_classes = [Diretor]
    nova_situacao = None  # definido em urls.py

    def post(self, request, pk):
        get_object_or_404(Atleta, pk=pk)
        justificativa = (request.data.get("justificativa") or "")[:300]
        try:
            atleta = mudar_situacao(pk, request.user, self.nova_situacao, justificativa)
        except SituacaoInvalida as e:
            return erro(status.HTTP_409_CONFLICT, "situacao_invalida", str(e))
        except UltimoDiretor as e:
            return erro(status.HTTP_409_CONFLICT, "ultimo_diretor", str(e))
        return Response(AtletaAdminSerializer(atleta).data)


class MudarPapelView(APIView):
    """POST atletas/{id}/papel/ {"papel": "diretor" | "atleta"}"""

    permission_classes = [Diretor]

    def post(self, request, pk):
        get_object_or_404(Atleta, pk=pk)
        dados = PapelSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        try:
            atleta = mudar_papel(pk, request.user, dados.validated_data["papel"])
        except SituacaoInvalida as e:
            return erro(status.HTTP_409_CONFLICT, "situacao_invalida", str(e))
        except UltimoDiretor as e:
            return erro(status.HTTP_409_CONFLICT, "ultimo_diretor", str(e))
        return Response(AtletaAdminSerializer(atleta).data)



# --- Meu perfil (UC04) ------------------------------------------------------


class PerfilView(generics.RetrieveUpdateAPIView):
    """GET perfil/ e PATCH perfil/ → dados do próprio usuário."""

    serializer_class = PerfilSerializer
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


class TrocaSenhaView(APIView):
    """POST perfil/senha/ {senha_atual, nova_senha, confirmacao} → 204."""

    def post(self, request):
        dados = TrocaSenhaSerializer(data=request.data, context={"usuario": request.user})
        dados.is_valid(raise_exception=True)
        request.user.set_password(dados.validated_data["nova_senha"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)