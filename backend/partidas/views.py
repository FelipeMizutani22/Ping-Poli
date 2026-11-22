"""Views do app partidas: adversários externos (UC15-a), registro e confirmação de partidas."""
from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response

from .models import AdversarioExterno
from .serializers import AdversarioExternoListaSerializer, AdversarioExternoSerializer
from .servicos import AdversarioJaExiste, cadastrar_adversario_externo


class AdversarioExternoListView(generics.ListCreateAPIView):
    """
    GET  adversarios-externos/?q=carlos → [{ id, nome, clube, partidas }]
    POST adversarios-externos/ { nome, clube } → 201 AdversarioExt · 409 "ja_existe" se o nome já existe.
    """

    pagination_class = None

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdversarioExternoListaSerializer
        return AdversarioExternoSerializer

    def get_queryset(self):
        qs = AdversarioExterno.objects.annotate(num_partidas=Count("partidas"))
        termo = (self.request.query_params.get("q") or "").strip()
        if termo:
            qs = qs.filter(nome__icontains=termo)
        return qs.order_by("nome")

    def create(self, request, *args, **kwargs):
        serializer = AdversarioExternoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            adversario = cadastrar_adversario_externo(**serializer.validated_data)
        except AdversarioJaExiste as e:
            return Response(
                {
                    "detail": str(e),
                    "codigo": "ja_existe",
                    "existente": AdversarioExternoSerializer(e.existente).data,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(AdversarioExternoSerializer(adversario).data, status=status.HTTP_201_CREATED)
