"""
Avisos de demonstração (08_DEMO_E_ENTREGA §1 · C4).
6 avisos, 2 fixados (um deles urgente), 1 expirado; a Ana leu metade.
Só 2 fixados de propósito: no roteiro da demo a Marina fixa um terceiro ("Treino aberto sábado").
"""
from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Aviso, AvisoLeitura

# (título, categoria, fixado, dias atrás, dias até expirar ou None, a Ana leu?, conteúdo)
AVISOS = [
    ("Mudança de local do treino de quinta", "urgente", True, 1, 7, False,
     "Atenção: nesta quinta o treino será no Ginásio 2 do CEPEUSP, porque o ginásio principal estará "
     "ocupado por um evento. O horário continua o mesmo, das 18h às 20h."),
    ("Inscrições abertas para a Copa Poli", "campeonato", True, 4, None, False,
     "As inscrições para a Copa Poli de Tênis de Mesa estão abertas no PingPoli, na página de Campeonatos. "
     "Há vagas limitadas por categoria; inscreva-se até o fim do prazo."),
    ("Novas raquetes da equipe", "geral", False, 6, None, True,
     "Chegaram as novas raquetes de uso coletivo. Elas ficam no armário da equipe; peça a chave a um "
     "Diretor e devolva ao final do treino."),
    ("Registrem as partidas no sistema", "geral", False, 10, None, True,
     "Lembrem de registrar no PingPoli todas as partidas jogadas, inclusive os amistosos. O adversário "
     "tem 7 dias para confirmar o placar; depois disso a partida é confirmada automaticamente."),
    ("Treino técnico de saque", "treino", False, 14, None, True,
     "No próximo treino de terça faremos uma sessão focada em saque curto e recepção. Tragam bolinhas "
     "extras, se tiverem."),
    ("Confraternização do semestre", "geral", False, 30, -3, False,
     "A confraternização do semestre aconteceu no último sábado. Obrigado a todos que participaram!"),
]


def seed(rng, ctx):
    hoje = timezone.localdate()
    ana = ctx["ana"]
    autores = ctx["diretores"]
    leitores_possiveis = [a for a in ctx["atletas"] if a != ana]

    leituras = []
    for i, (titulo, categoria, fixado, dias_atras, expira_em, ana_leu, conteudo) in enumerate(AVISOS):
        publicado = timezone.make_aware(datetime.combine(hoje - timedelta(days=dias_atras), time(10, 0)))
        aviso = Aviso.objects.create(
            autor=autores[i % len(autores)], titulo=titulo, conteudo=conteudo, categoria=categoria,
            fixado=fixado, data_publicacao=publicado,
            data_expiracao=hoje + timedelta(days=expira_em) if expira_em is not None else None,
        )
        # Leituras parciais: a Ana conforme a tabela; os outros atletas, ao acaso.
        leitores = [ana] if ana_leu else []
        leitores += [a for a in leitores_possiveis if rng.random() < 0.5]
        leituras += [
            AvisoLeitura(aviso=aviso, atleta=a, data_leitura=publicado + timedelta(hours=rng.randint(1, 48)))
            for a in leitores
        ]
    AvisoLeitura.objects.bulk_create(leituras)
    return f"{len(AVISOS)} avisos, {len(leituras)} leituras"
