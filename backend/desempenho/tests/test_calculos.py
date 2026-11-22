from datetime import date

from django.test import SimpleTestCase

from desempenho.calculos import (
    evolucao_mensal,
    indicadores,
    mais_enfrentados,
    por_competicao,
    recentes,
    resolver_periodo,
    sequencia_atual,
)


class SequenciaAtualTests(SimpleTestCase):
    def test_sem_partidas_retorna_none(self):
        self.assertIsNone(sequencia_atual([]))

    def test_conta_vitorias_recentes_com_lista_fora_de_ordem(self):
        linhas = [
            {"partida_id": 2, "data": date(2026, 11, 19), "venceu": True},
            {"partida_id": 1, "data": date(2026, 11, 18), "venceu": False},
            {"partida_id": 3, "data": date(2026, 11, 20), "venceu": True},
        ]
        original = linhas.copy()

        self.assertEqual(
            sequencia_atual(linhas),
            {"tipo": "V", "quantidade": 2},
        )
        self.assertEqual(linhas, original)

    def test_conta_derrotas_quando_todas_as_partidas_sao_derrotas(self):
        linhas = [
            {"partida_id": 1, "data": date(2026, 11, 18), "venceu": False},
            {"partida_id": 2, "data": date(2026, 11, 19), "venceu": False},
        ]

        self.assertEqual(
            sequencia_atual(linhas),
            {"tipo": "D", "quantidade": 2},
        )

    def test_mesma_data_usa_maior_id_como_mais_recente(self):
        linhas = [
            {"partida_id": 1, "data": date(2026, 11, 20), "venceu": True},
            {"partida_id": 2, "data": date(2026, 11, 20), "venceu": False},
        ]

        self.assertEqual(
            sequencia_atual(linhas),
            {"tipo": "D", "quantidade": 1},
        )

class IndicadoresTests(SimpleTestCase):
    def test_sem_partidas_retorna_totais_zerados(self):
        self.assertEqual(
            indicadores([]),
            {
                "partidas": 0,
                "vitorias": 0,
                "derrotas": 0,
                "pct_vitorias": 0.0,
                "sets_pro": 0,
                "sets_contra": 0,
                "saldo_sets": 0,
                "pontos_pro": 0,
                "pontos_contra": 0,
                "sequencia_atual": None,
            },
        )

    def test_calcula_totais_percentual_e_sequencia(self):
        linhas = [
            {
                "partida_id": 1,
                "data": date(2026, 11, 18),
                "venceu": False,
                "sets_pro": 2,
                "sets_contra": 3,
                "pontos_pro": 45,
                "pontos_contra": 49,
            },
            {
                "partida_id": 2,
                "data": date(2026, 11, 19),
                "venceu": True,
                "sets_pro": 3,
                "sets_contra": 1,
                "pontos_pro": 41,
                "pontos_contra": 33,
            },
            {
                "partida_id": 3,
                "data": date(2026, 11, 20),
                "venceu": True,
                "sets_pro": 3,
                "sets_contra": 0,
                "pontos_pro": 33,
                "pontos_contra": 21,
            },
        ]

        self.assertEqual(
            indicadores(linhas),
            {
                "partidas": 3,
                "vitorias": 2,
                "derrotas": 1,
                "pct_vitorias": 66.7,
                "sets_pro": 8,
                "sets_contra": 4,
                "saldo_sets": 4,
                "pontos_pro": 119,
                "pontos_contra": 103,
                "sequencia_atual": {"tipo": "V", "quantidade": 2},
            },
        )

class EvolucaoMensalTests(SimpleTestCase):
    def test_mes_sem_jogos_e_diferente_de_mes_com_derrotas(self):
        linhas = [
            {"data": date(2026, 6, 10), "venceu": True},
            {"data": date(2026, 6, 20), "venceu": False},
            {"data": date(2026, 8, 15), "venceu": False},
        ]

        self.assertEqual(
            evolucao_mensal(linhas, date(2026, 6, 1), date(2026, 8, 31)),
            [
                {
                    "mes": "2026-06",
                    "partidas": 2,
                    "vitorias": 1,
                    "pct_vitorias": 50.0,
                },
                {
                    "mes": "2026-07",
                    "partidas": 0,
                    "vitorias": 0,
                    "pct_vitorias": None,
                },
                {
                    "mes": "2026-08",
                    "partidas": 1,
                    "vitorias": 0,
                    "pct_vitorias": 0.0,
                },
            ],
        )

    def test_periodo_vazio_inclui_meses_na_virada_do_ano(self):
        resultado = evolucao_mensal(
            [], date(2025, 12, 15), date(2026, 2, 10)
        )

        self.assertEqual(
            [item["mes"] for item in resultado],
            ["2025-12", "2026-01", "2026-02"],
        )
        for item in resultado:
            self.assertEqual(item["partidas"], 0)
            self.assertEqual(item["vitorias"], 0)
            self.assertIsNone(item["pct_vitorias"])

    def test_respeita_os_dias_limites_do_periodo(self):
        linhas = [
            {"data": date(2026, 11, 9), "venceu": False},
            {"data": date(2026, 11, 10), "venceu": True},
            {"data": date(2026, 11, 20), "venceu": True},
            {"data": date(2026, 11, 21), "venceu": False},
        ]

        self.assertEqual(
            evolucao_mensal(linhas, date(2026, 11, 10), date(2026, 11, 20)),
            [
                {
                    "mes": "2026-11",
                    "partidas": 2,
                    "vitorias": 2,
                    "pct_vitorias": 100.0,
                }
            ],
        )

    def test_rejeita_periodo_invertido(self):
        with self.assertRaises(ValueError):
            evolucao_mensal([], date(2026, 11, 20), date(2026, 11, 10))

class PorCompeticaoTests(SimpleTestCase):
    def test_sem_partidas_retorna_lista_vazia(self):
        self.assertEqual(por_competicao([]), [])

    def test_agrupa_resultados_e_separa_campeonatos_com_mesmo_nome(self):
        linhas = [
            {"campeonato_id": 1, "competicao": "Copa Poli", "venceu": True},
            {"campeonato_id": 1, "competicao": "Copa Poli", "venceu": False},
            {"campeonato_id": 2, "competicao": "Copa Poli", "venceu": False},
            {"campeonato_id": None, "competicao": "Amistoso/Treino", "venceu": True},
            {"campeonato_id": None, "competicao": "Amistoso/Treino", "venceu": True},
        ]

        self.assertCountEqual(
            por_competicao(linhas),
            [
                {
                    "competicao": "Copa Poli",
                    "campeonato_id": 1,
                    "vitorias": 1,
                    "derrotas": 1,
                },
                {
                    "competicao": "Copa Poli",
                    "campeonato_id": 2,
                    "vitorias": 0,
                    "derrotas": 1,
                },
                {
                    "competicao": "Amistoso/Treino",
                    "campeonato_id": None,
                    "vitorias": 2,
                    "derrotas": 0,
                },
            ],
        )

def linha_exemplo(partida_id=1, **alteracoes):
    linha = {
        "partida_id": partida_id,
        "data": date(2026, 11, 18),
        "campeonato_id": None,
        "competicao": "Amistoso/Treino",
        "tipo_adversario": "poli",
        "adversario_id": 5,
        "adversario_nome": "Bruno Kato",
        "sets_pro": 3,
        "sets_contra": 1,
        "pontos_pro": 41,
        "pontos_contra": 33,
        "venceu": True,
    }
    linha.update(alteracoes)
    return linha


class ResolverPeriodoTests(SimpleTestCase):
    def test_periodos_mensais_e_virada_do_ano(self):
        hoje = date(2026, 11, 21)
        casos = [
            ("3m", date(2026, 9, 1)),
            ("6m", date(2026, 6, 1)),
            ("12m", date(2025, 12, 1)),
        ]

        for periodo, esperado in casos:
            with self.subTest(periodo=periodo):
                self.assertEqual(
                    resolver_periodo(periodo, hoje=hoje),
                    (esperado, hoje),
                )

        self.assertEqual(
            resolver_periodo("3m", hoje=date(2026, 1, 15)),
            (date(2025, 11, 1), date(2026, 1, 15)),
        )

    def test_todo_historico_com_e_sem_partidas(self):
        hoje = date(2026, 11, 21)

        self.assertEqual(
            resolver_periodo(
                "tudo", hoje=hoje, primeira_data=date(2024, 5, 17)
            ),
            (date(2024, 5, 17), hoje),
        )
        self.assertEqual(
            resolver_periodo("tudo", hoje=hoje),
            (date(2026, 11, 1), hoje),
        )

    def test_periodo_personalizado_inclusive_um_unico_dia(self):
        hoje = date(2026, 11, 21)

        self.assertEqual(
            resolver_periodo(
                "custom",
                hoje=hoje,
                inicio=date(2026, 7, 10),
                fim=date(2026, 8, 20),
            ),
            (date(2026, 7, 10), date(2026, 8, 20)),
        )
        self.assertEqual(
            resolver_periodo("custom", hoje=hoje, inicio=hoje, fim=hoje),
            (hoje, hoje),
        )

    def test_rejeita_periodos_invalidos(self):
        hoje = date(2026, 11, 21)
        casos = [
            {"periodo": "inexistente"},
            {"periodo": "custom"},
            {"periodo": "custom", "inicio": hoje},
            {
                "periodo": "custom",
                "inicio": hoje,
                "fim": date(2026, 11, 20),
            },
            {
                "periodo": "custom",
                "inicio": hoje,
                "fim": date(2026, 11, 22),
            },
            {
                "periodo": "tudo",
                "primeira_data": date(2026, 11, 22),
            },
        ]

        for caso in casos:
            with self.subTest(caso=caso):
                with self.assertRaises(ValueError):
                    resolver_periodo(hoje=hoje, **caso)


class MaisEnfrentadosTests(SimpleTestCase):
    def test_sem_partidas(self):
        self.assertEqual(mais_enfrentados([]), [])

    def test_separa_poli_e_externo_com_mesmo_id(self):
        linhas = [
            linha_exemplo(1),
            linha_exemplo(2, venceu=False),
            linha_exemplo(
                3,
                tipo_adversario="externo",
                adversario_nome="Carlos Pereira",
            ),
        ]

        self.assertEqual(
            mais_enfrentados(linhas),
            [
                {
                    "adversario": {
                        "tipo": "poli",
                        "id": 5,
                        "nome": "Bruno Kato",
                    },
                    "partidas": 2,
                    "vitorias": 1,
                    "derrotas": 1,
                },
                {
                    "adversario": {
                        "tipo": "externo",
                        "id": 5,
                        "nome": "Carlos Pereira",
                    },
                    "partidas": 1,
                    "vitorias": 1,
                    "derrotas": 0,
                },
            ],
        )

    def test_ordena_por_quantidade_nome_e_limita_a_cinco(self):
        nomes = ["Zelia", "Eva", "Davi", "Carla", "Bruno", "Ana"]
        linhas = [
            linha_exemplo(i, adversario_id=i, adversario_nome=nome)
            for i, nome in enumerate(nomes, start=1)
        ]
        linhas.append(
            linha_exemplo(7, adversario_id=1, adversario_nome="Zelia")
        )

        resultado = mais_enfrentados(linhas)

        self.assertEqual(
            [item["adversario"]["nome"] for item in resultado],
            ["Zelia", "Ana", "Bruno", "Carla", "Davi"],
        )
        self.assertEqual(resultado[0]["partidas"], 2)


class RecentesTests(SimpleTestCase):
    def test_sem_partidas(self):
        self.assertEqual(recentes([]), [])

    def test_formato_da_resposta(self):
        self.assertEqual(
            recentes([linha_exemplo()]),
            [
                {
                    "partida_id": 1,
                    "data": date(2026, 11, 18),
                    "competicao": "Amistoso/Treino",
                    "adversario": {
                        "tipo": "poli",
                        "id": 5,
                        "nome": "Bruno Kato",
                    },
                    "sets_pro": 3,
                    "sets_contra": 1,
                    "venceu": True,
                    "placar": "3–1",
                }
            ],
        )

    def test_ordena_por_data_id_limita_dez_e_preserva_entrada(self):
        linhas = [linha_exemplo(i) for i in range(1, 13)]
        linhas.append(linha_exemplo(13, data=date(2026, 11, 1)))
        original = [linha.copy() for linha in linhas]

        resultado = recentes(linhas)

        self.assertEqual(
            [item["partida_id"] for item in resultado],
            list(range(12, 2, -1)),
        )
        self.assertEqual(linhas, original)

class PerspectivaTests(SimpleTestCase):
    def test_mesma_partida_conta_vitoria_e_derrota_para_atletas_distintos(self):
        linha_ana = linha_exemplo()
        linha_bruno = linha_exemplo(
            adversario_id=3,
            adversario_nome="Ana Lima",
            sets_pro=1,
            sets_contra=3,
            pontos_pro=33,
            pontos_contra=41,
            venceu=False,
        )

        ana = indicadores([linha_ana])
        bruno = indicadores([linha_bruno])

        self.assertEqual(ana["partidas"], 1)
        self.assertEqual(bruno["partidas"], 1)
        self.assertEqual(ana["vitorias"], 1)
        self.assertEqual(bruno["derrotas"], 1)
        self.assertEqual(ana["pct_vitorias"], 100.0)
        self.assertEqual(bruno["pct_vitorias"], 0.0)
        self.assertEqual(ana["saldo_sets"], 2)
        self.assertEqual(bruno["saldo_sets"], -2)
        self.assertEqual(ana["pontos_pro"], bruno["pontos_contra"])
        self.assertEqual(ana["pontos_contra"], bruno["pontos_pro"])