from copy import deepcopy
from datetime import date

from django.test import SimpleTestCase

from desempenho.calculos import partidas_por_mes, ranking_equipe


def criar_linhas(vitorias, derrotas, *, primeiro_id=1, sets_derrota=1):
    linhas = []

    for indice in range(vitorias + derrotas):
        venceu = indice < vitorias
        linhas.append({
            "partida_id": primeiro_id + indice,
            "data": date(2026, 11, 10),
            "venceu": venceu,
            "sets_pro": 3 if venceu else sets_derrota,
            "sets_contra": 1 if venceu else 3,
            "pontos_pro": 40 if venceu else 30,
            "pontos_contra": 30 if venceu else 40,
        })

    return linhas


def participante(identificador, nome, vitorias, derrotas, **opcoes):
    return {
        "atleta": {
            "id": identificador,
            "nome": nome,
            "nusp": 10000000 + identificador,
        },
        "linhas": criar_linhas(vitorias, derrotas, **opcoes),
    }


class RankingEquipeTests(SimpleTestCase):
    def test_vazio(self):
        self.assertEqual(ranking_equipe([]), [])

    def test_minimo_cinco_e_formato(self):
        ana = participante(1, "Ana", 3, 2)
        dados = [
            participante(2, "Bruno", 4, 0),
            participante(3, "Carla", 0, 0),
            ana,
        ]

        self.assertEqual(ranking_equipe(dados), [{
            "posicao": 1,
            "atleta": ana["atleta"],
            "partidas": 5,
            "vitorias": 3,
            "pct_vitorias": 60.0,
            "saldo_sets": 2,
        }])

    def test_percentual_tem_prioridade_sobre_saldo(self):
        dados = [
            participante(1, "Ana", 7, 3),
            participante(2, "Bruno", 4, 1),
        ]
        resultado = ranking_equipe(dados)
        self.assertEqual(
            [item["atleta"]["nome"] for item in resultado],
            ["Bruno", "Ana"],
        )

    def test_desempate_por_saldo_sets(self):
        dados = [
            participante(1, "Ana", 3, 2),
            participante(2, "Bruno", 3, 2, sets_derrota=2),
        ]
        resultado = ranking_equipe(dados)
        self.assertEqual(
            [item["atleta"]["nome"] for item in resultado],
            ["Bruno", "Ana"],
        )

    def test_desempate_por_quantidade_partidas(self):
        dados = [
            participante(1, "Ana", 3, 3),
            participante(2, "Bruno", 5, 5),
        ]
        resultado = ranking_equipe(dados)
        self.assertEqual(
            [item["atleta"]["nome"] for item in resultado],
            ["Bruno", "Ana"],
        )

    def test_desempate_por_nome_e_posicoes(self):
        dados = [
            participante(1, "Bruno", 3, 2),
            participante(2, "Ana", 3, 2),
        ]
        resultado = ranking_equipe(dados)
        self.assertEqual(
            [item["atleta"]["nome"] for item in resultado],
            ["Ana", "Bruno"],
        )
        self.assertEqual([item["posicao"] for item in resultado], [1, 2])

    def test_nao_altera_entrada(self):
        dados = [participante(1, "Ana", 3, 2)]
        original = deepcopy(dados)
        ranking_equipe(dados)
        self.assertEqual(dados, original)


class PartidasPorMesTests(SimpleTestCase):
    def test_partida_poli_conta_apenas_uma_vez(self):
        ana = criar_linhas(1, 0)[0]
        bruno = {
            **ana,
            "venceu": False,
            "sets_pro": 1,
            "sets_contra": 3,
            "pontos_pro": 30,
            "pontos_contra": 40,
        }
        outra = criar_linhas(1, 0, primeiro_id=2)[0]

        resultado = partidas_por_mes(
            [ana, bruno, outra],
            date(2026, 11, 1),
            date(2026, 11, 30),
        )

        self.assertEqual(resultado, [{"mes": "2026-11", "partidas": 2}])

    def test_meses_vazios_e_limites_do_periodo(self):
        linhas = [
            {**criar_linhas(1, 0, primeiro_id=i)[0], "data": data}
            for i, data in enumerate([
                date(2026, 9, 9),
                date(2026, 9, 10),
                date(2026, 11, 20),
                date(2026, 11, 21),
            ], start=1)
        ]

        self.assertEqual(
            partidas_por_mes(
                linhas, date(2026, 9, 10), date(2026, 11, 20)
            ),
            [
                {"mes": "2026-09", "partidas": 1},
                {"mes": "2026-10", "partidas": 0},
                {"mes": "2026-11", "partidas": 1},
            ],
        )

    def test_sem_partidas(self):
        self.assertEqual(
            partidas_por_mes(
                [], date(2026, 11, 1), date(2026, 11, 30)
            ),
            [{"mes": "2026-11", "partidas": 0}],
        )