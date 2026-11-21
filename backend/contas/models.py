"""
Modelos do app contas: Curso e Atleta (usuário do sistema).
Correspondem às tabelas "curso" e "atleta" do diagrama ER (docs/entregas/).
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Curso(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "curso"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class AtletaManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **campos):
        if not email:
            raise ValueError("O e-mail é obrigatório")
        atleta = self.model(email=self.normalize_email(email).lower(), **campos)
        atleta.set_password(password)
        atleta.save(using=self._db)
        return atleta

    def create_superuser(self, email, password=None, **campos):
        campos["is_superuser"] = True
        campos["papel"] = Atleta.Papel.DIRETOR
        campos["situacao"] = Atleta.Situacao.ATIVA
        return self.create_user(email, password, **campos)


class Atleta(AbstractBaseUser, PermissionsMixin):
    class Papel(models.TextChoices):
        ATLETA = "atleta", "Atleta"
        DIRETOR = "diretor", "Diretor de Modalidade"

    class Situacao(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ATIVA = "ativa", "Ativa"
        RECUSADA = "recusada", "Recusada"
        INATIVA = "inativa", "Inativa"

    class MaoDominante(models.TextChoices):
        DESTRO = "destro", "Destro"
        CANHOTO = "canhoto", "Canhoto"

    # Campos herdados do Django, sobrescritos para manter os nomes de coluna do ER.
    password = models.CharField("senha", max_length=255, db_column="senha_hash")
    last_login = models.DateTimeField("último acesso", null=True, blank=True, db_column="ultimo_acesso")

    nome = models.CharField(max_length=100)
    nusp = models.PositiveIntegerField("NUSP", unique=True)
    email = models.EmailField("e-mail", max_length=100, unique=True)
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name="atletas")
    ano_ingresso = models.PositiveSmallIntegerField("ano de ingresso")
    telefone = models.CharField(max_length=20, blank=True)
    foto = models.CharField(max_length=255, blank=True)
    mao_dominante = models.CharField("mão dominante", max_length=10, blank=True, choices=MaoDominante.choices)
    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.ATLETA)
    situacao = models.CharField("situação", max_length=20, choices=Situacao.choices, default=Situacao.PENDENTE)
    motivo_recusa = models.CharField(max_length=300, blank=True)
    avaliado_por = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="avaliados"
    )
    data_solicitacao = models.DateTimeField(default=timezone.now)
    data_avaliacao = models.DateTimeField(null=True, blank=True)
    tentativas_login = models.PositiveSmallIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)

    objects = AtletaManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome", "nusp", "curso", "ano_ingresso"]

    class Meta:
        db_table = "atleta"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.email})"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    @property
    def is_staff(self):
        """Acesso ao /admin/: só superusuários (a Diretora dos dados de teste)."""
        return self.is_superuser

    @property
    def eh_diretor(self):
        return self.papel == self.Papel.DIRETOR