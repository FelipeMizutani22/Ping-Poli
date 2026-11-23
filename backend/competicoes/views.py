"""API de campeonatos; inscrições são tratadas na D6."""
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from contas.permissoes import AtletaAtivo, Diretor
from .models import Campeonato, Categoria, Inscricao
from .serializers import CampeonatoSerializer, CampeonatoEntradaSerializer, CancelamentoSerializer
from .servicos import criar_campeonato, editar_campeonato, cancelar_campeonato, sincronizar_status


def campeonatos_para(usuario):
    categorias = Categoria.objects.annotate(
        total_inscritos=Count('inscricoes', filter=Q(inscricoes__status='ativa')),
        inscrito=Exists(Inscricao.objects.filter(categoria_id=OuterRef('pk'), atleta=usuario, status='ativa')),
    ).order_by('nome', 'id')
    return Campeonato.objects.prefetch_related(Prefetch('categorias', queryset=categorias)).order_by('-data_inicio', 'id')


class CampeonatoMixin:
    serializer_class = CampeonatoSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Executar somente depois de autenticar e conferir as permissões.
        sincronizar_status()

    def get_queryset(self):
        return campeonatos_para(self.request.user)

    def saida(self, campeonato):
        return self.get_serializer(self.get_queryset().get(pk=campeonato.pk)).data

    def get_permissions(self):
        return [AtletaAtivo()] if self.request.method in ('GET', 'HEAD', 'OPTIONS') else [Diretor()]


class CampeonatoListCreateView(CampeonatoMixin, generics.ListCreateAPIView):
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        filtro = self.request.query_params.get('status')
        if filtro:
            if filtro not in Campeonato.Status.values:
                raise serializers.ValidationError({'status': ['Status inválido.']})
            queryset = queryset.filter(status=filtro)
        return queryset

    def create(self, request, *args, **kwargs):
        entrada = CampeonatoEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        campeonato = criar_campeonato(request.user, entrada.validated_data)
        return Response(CampeonatoSerializer(campeonatos_para(request.user).get(pk=campeonato.pk)).data,
                        status=status.HTTP_201_CREATED)


class CampeonatoDetailView(CampeonatoMixin, generics.RetrieveAPIView):
    def patch(self, request, *args, **kwargs):
        campeonato = self.get_object()
        campeonato = editar_campeonato(campeonato.pk, request.data, request.user)
        return Response(self.saida(campeonato))


class CampeonatoCancelarView(CampeonatoMixin, generics.GenericAPIView):
    permission_classes = [Diretor]

    def get_permissions(self):
        return [Diretor()]

    def post(self, request, *args, **kwargs):
        campeonato = self.get_object()
        entrada = CancelamentoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        campeonato = cancelar_campeonato(campeonato.pk, request.user, entrada.validated_data['motivo'])
        return Response(self.saida(campeonato))
