from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from competicoes.models import Campeonato, Categoria
from contas.serializers import AtletaResumoSerializer
from .models import AdversarioExterno, Partida
from .regras import resultado, validar_placar

MSG_DATA_FUTURA = "A data da partida não pode ser futura"
MSG_CONTRA_SI = "Você não pode registrar uma partida contra si mesmo"
MSG_ADVERSARIO_INATIVO = "O adversário precisa ser um atleta com conta ativa"
MSG_CATEGORIA = "A categoria não pertence ao campeonato escolhido"
MSG_OBRIGATORIO = "Este campo é obrigatório."


# ---------- Adversários externos (B1) ----------

class AdversarioExternoSerializer(serializers.ModelSerializer):
    """Formato curto (AdversarioExt do contrato): { id, nome, clube }."""

    nome = serializers.CharField(min_length=3, max_length=100, trim_whitespace=True)
    clube = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)

    class Meta:
        model = AdversarioExterno
        fields = ["id", "nome", "clube"]


class AdversarioExternoListaSerializer(AdversarioExternoSerializer):
    """Item da busca: o AdversarioExt mais o número de partidas contra ele."""

    partidas = serializers.IntegerField(source="num_partidas", read_only=True)

    class Meta(AdversarioExternoSerializer.Meta):
        fields = ["id", "nome", "clube", "partidas"]


# ---------- Registrar partida (entrada do POST partidas/) ----------

class SetEntradaSerializer(serializers.Serializer):
    pontos_atleta = serializers.IntegerField()
    pontos_adversario = serializers.IntegerField()


class RegistrarPartidaSerializer(serializers.Serializer):
    """Valida o formulário do UC15. Só validação: quem grava é servicos.registrar_partida."""

    data_jogo = serializers.DateField()
    campeonato = serializers.PrimaryKeyRelatedField(queryset=Campeonato.objects.all(), allow_null=True, default=None)
    categoria = serializers.PrimaryKeyRelatedField(queryset=Categoria.objects.all(), allow_null=True, default=None)
    fase = serializers.CharField(max_length=50, allow_blank=True, default="")
    tipo_adversario = serializers.ChoiceField(choices=Partida.TipoAdversario.choices)
    adversario = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), allow_null=True, default=None
    )
    adversario_externo = serializers.PrimaryKeyRelatedField(
        queryset=AdversarioExterno.objects.all(), allow_null=True, default=None
    )
    formato = serializers.ChoiceField(choices=Partida.Formato.choices)
    sets = SetEntradaSerializer(many=True)
    observacoes = serializers.CharField(max_length=300, allow_blank=True, default="")

    def validate_data_jogo(self, valor):
        if valor > timezone.localdate():
            raise serializers.ValidationError(MSG_DATA_FUTURA)  # UC15-e
        return valor

    def validate(self, dados):
        erros = {}
        # Na moderação (UC17) quem edita é o Diretor, mas o registrante continua sendo o jogador original.
        usuario = self.context.get("registrante") or self.context["request"].user

        # Adversário: exatamente um dos dois, conforme o tipo (constraint {xor} do ER)
        if dados["tipo_adversario"] == Partida.TipoAdversario.POLI:
            dados["adversario_externo"] = None
            adversario = dados["adversario"]
            if adversario is None:
                erros["adversario"] = [MSG_OBRIGATORIO]
            elif adversario.pk == usuario.pk:
                erros["adversario"] = [MSG_CONTRA_SI]
            elif adversario.situacao != "ativa":
                erros["adversario"] = [MSG_ADVERSARIO_INATIVO]
        else:
            dados["adversario"] = None
            if dados["adversario_externo"] is None:
                erros["adversario_externo"] = [MSG_OBRIGATORIO]

        # Categoria: só existe com campeonato, e precisa ser desse campeonato
        if dados["campeonato"] is None:
            dados["categoria"] = None
        elif dados["categoria"] is not None and dados["categoria"].campeonato_id != dados["campeonato"].id:
            erros["categoria"] = [MSG_CATEGORIA]

        # Placar set a set (F3.1 · UC15-f)
        erros_placar = validar_placar(dados["sets"], dados["formato"])
        if erros_placar:
            erros["sets"] = erros_placar

        if erros:
            raise serializers.ValidationError(erros)
        return dados


# ---------- Contestar partida (entrada do POST partidas/{id}/contestar/) ----------

class ContestarSerializer(serializers.Serializer):
    """UC16-a: justificativa obrigatória e placar proposto opcional, com as regras do UC15."""

    justificativa = serializers.CharField(min_length=10, max_length=500, trim_whitespace=True)
    sets = SetEntradaSerializer(many=True, required=False, default=list)

    def validate_sets(self, sets):
        if sets:
            erros = validar_placar(sets, self.context["partida"].formato)
            if erros:
                raise serializers.ValidationError(erros)
        return sets


# ---------- Partida (saída, formato "Partida" do contrato) ----------

def _set_dto(s):
    return {"numero": s.numero, "pontos_atleta": s.pontos_atleta, "pontos_adversario": s.pontos_adversario}


def _data_hora(valor):
    return serializers.DateTimeField().to_representation(valor) if valor else None


class PartidaSerializer(serializers.ModelSerializer):
    atleta = AtletaResumoSerializer(read_only=True)
    adversario = AtletaResumoSerializer(read_only=True)
    adversario_externo = AdversarioExternoSerializer(read_only=True)
    competicao = serializers.SerializerMethodField()
    categoria = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    placar_sets = serializers.SerializerMethodField()
    vencedor = serializers.SerializerMethodField()
    dias_para_responder = serializers.SerializerMethodField()
    contestacao = serializers.SerializerMethodField()

    class Meta:
        model = Partida
        fields = [
            "id", "data_jogo", "competicao", "categoria", "fase", "tipo_adversario",
            "atleta", "adversario", "adversario_externo", "formato", "status",
            "sets", "placar_sets", "vencedor", "observacoes", "data_registro", "data_confirmacao",
            "dias_para_responder", "contestacao",
        ]

    # Os sets vêm pré-carregados (prefetch_related) e são filtrados em Python, sem nova consulta.
    def _oficiais(self, obj):
        return sorted((s for s in obj.sets.all() if s.contestacao_id is None), key=lambda s: s.numero)

    def _resultado(self, obj):
        return resultado([_set_dto(s) for s in self._oficiais(obj)])

    def get_competicao(self, obj):
        if obj.campeonato is None:
            return {"tipo": "amistoso", "campeonato_id": None, "nome": "Amistoso/Treino"}
        return {"tipo": "campeonato", "campeonato_id": obj.campeonato.id, "nome": obj.campeonato.nome}

    def get_categoria(self, obj):
        return {"id": obj.categoria.id, "nome": obj.categoria.nome} if obj.categoria else None

    def get_sets(self, obj):
        return [_set_dto(s) for s in self._oficiais(obj)]

    def get_placar_sets(self, obj):
        r = self._resultado(obj)
        return {"atleta": r["sets_atleta"], "adversario": r["sets_adversario"]}

    def get_vencedor(self, obj):
        return self._resultado(obj)["vencedor"]

    def get_dias_para_responder(self, obj):
        if obj.status != Partida.Status.PENDENTE:
            return None
        dias = (timezone.localdate() - timezone.localtime(obj.data_registro).date()).days
        return max(0, 7 - dias)

    def get_contestacao(self, obj):
        contestacoes = sorted(obj.contestacoes.all(), key=lambda c: c.data_contestacao)
        if not contestacoes:
            return None
        c = contestacoes[-1]
        propostos = sorted((s for s in obj.sets.all() if s.contestacao_id == c.id), key=lambda s: s.numero)
        return {
            "id": c.id,
            "contestante": AtletaResumoSerializer(c.contestante).data,
            "justificativa": c.justificativa,
            "sets_propostos": [_set_dto(s) for s in propostos],
            "data_contestacao": _data_hora(c.data_contestacao),
            "resolvida_por": AtletaResumoSerializer(c.resolvida_por).data if c.resolvida_por else None,
            "motivo_decisao": c.motivo_decisao,
            "data_resolucao": _data_hora(c.data_resolucao),
        }
