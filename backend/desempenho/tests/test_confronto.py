from copy import deepcopy
from datetime import date

from django.test import SimpleTestCase

from desempenho.calculos import confronto_direto


A = {"id": 1, "nome": "Ana", "nusp": 10000001}
B = {"id": 2, "nome": "Bruno", "nusp": 10000002}


def jogo(identificador, dia, sets_pro=3, sets_contra=1):
    venceu = sets_pro > sets_contra
    return {
        "partida_id": identificador,
        "data": date(2026, 11, dia),
        "campeonato_id": None,
        "competicao": "Amistoso/Treino",
        "tipo_adversario": "poli",
        "adversario_id": B["id"],
        "adversario_nome": B["nome"],
        "sets_pro": sets_pro,
        "sets_contra": sets_contra,
        "pontos_pro": 40 if venceu else 30,
        "pontos_contra": 30 if venceu else 40,
        "venceu": venceu,
    }


class ConfrontoDiretoTests(SimpleTestCase):
    def test_sem_partidas(self):
        resultado = confronto_direto([], A, B)

        self.assertEqual(resultado["retrospecto"], {
            "vitorias_a": 0,
            "vitorias_b": 0,
            "sets_a": 0,
            "sets_b": 0,
            "pontos_a": 0,
            "pontos_b": 0,
            "pct_a": 0.0,
            "pct_b": 0.0,
        })
        self.assertEqual(resultado["partidas"], [])
        self.assertEqual(resultado["acumulado"], [])
        self.assertIsNone(resultado["ultima_partida"])
        self.assertIsNone(resultado["maior_vitoria_a"])
        self.assertIsNone(resultado["maior_vitoria_b"])
        self.assertIsNone(resultado["indicadores_a"]["sequencia_atual"])
        self.assertIsNone(resultado["indicadores_b"]["sequencia_atual"])

    def test_retrospecto_e_inversao_dos_indicadores(self):
        linhas = [
            jogo(1, 1, 3, 1),
            jogo(2, 2, 1, 3),
            jogo(3, 3, 3, 0),
        ]
        resultado = confronto_direto(linhas, A, B)

        self.assertEqual(resultado["retrospecto"], {
            "vitorias_a": 2,
            "vitorias_b": 1,
            "sets_a": 7,
            "sets_b": 4,
            "pontos_a": 110,
            "pontos_b": 100,
            "pct_a": 66.7,
            "pct_b": 33.3,
        })

        resumo_a = resultado["indicadores_a"]
        resumo_b = resultado["indicadores_b"]

        self.assertEqual(resumo_a["saldo_sets"], 3)
        self.assertEqual(resumo_b["saldo_sets"], -3)
        self.assertEqual(resumo_b["sets_contra"], 7)
        self.assertEqual(resumo_b["pontos_contra"], 110)
        self.assertEqual(resumo_b["derrotas"], 2)
        self.assertEqual(
            resumo_a["sequencia_atual"], {"tipo": "V", "quantidade": 1}
        )
        self.assertEqual(
            resumo_b["sequencia_atual"], {"tipo": "D", "quantidade": 1}
        )

    def test_ordem_cronologica_acumulado_e_ultima(self):
        linhas = [
            jogo(3, 2),
            jogo(2, 1, 1, 3),
            jogo(1, 1),
        ]
        resultado = confronto_direto(linhas, A, B)

        self.assertEqual(
            [p["partida_id"] for p in resultado["partidas"]],
            [1, 2, 3],
        )
        self.assertEqual(resultado["ultima_partida"]["partida_id"], 3)
        self.assertEqual(resultado["acumulado"], [
            {"data": date(2026, 11, 1), "vitorias_a": 1, "vitorias_b": 0},
            {"data": date(2026, 11, 1), "vitorias_a": 1, "vitorias_b": 1},
            {"data": date(2026, 11, 2), "vitorias_a": 2, "vitorias_b": 1},
        ])

    def test_maiores_vitorias_priorizam_diferenca_de_sets(self):
        linhas = [
            jogo(1, 1, 3, 0),
            jogo(2, 2, 3, 2),
            jogo(3, 3, 0, 3),
            jogo(4, 4, 2, 3),
        ]
        resultado = confronto_direto(linhas, A, B)

        self.assertEqual(resultado["maior_vitoria_a"]["partida_id"], 1)
        self.assertEqual(resultado["maior_vitoria_b"]["partida_id"], 3)
        self.assertEqual(resultado["maior_vitoria_b"]["placar"], "0–3")
        self.assertFalse(resultado["maior_vitoria_b"]["venceu"])

    def test_maiores_vitorias_desempatam_por_data_e_id(self):
        for sets_pro, sets_contra, campo in [
            (3, 0, "maior_vitoria_a"),
            (0, 3, "maior_vitoria_b"),
        ]:
            with self.subTest(campo=campo):
                linhas = [
                    jogo(9, 1, sets_pro, sets_contra),
                    jogo(2, 2, sets_pro, sets_contra),
                    jogo(3, 2, sets_pro, sets_contra),
                ]
                resultado = confronto_direto(linhas, A, B)
                self.assertEqual(resultado[campo]["partida_id"], 3)

    def test_sem_vitoria_de_um_dos_lados(self):
        resultado = confronto_direto([jogo(1, 1)], A, B)
        self.assertIsNone(resultado["maior_vitoria_b"])
        self.assertEqual(resultado["retrospecto"]["pct_a"], 100.0)

        resultado = confronto_direto([jogo(1, 1, 1, 3)], A, B)
        self.assertIsNone(resultado["maior_vitoria_a"])
        self.assertEqual(resultado["retrospecto"]["pct_b"], 100.0)

    def test_historico_nao_tem_limite_de_dez(self):
        linhas = [jogo(i, i) for i in range(1, 13)]
        resultado = confronto_direto(linhas, A, B)

        self.assertEqual(len(resultado["partidas"]), 12)
        self.assertEqual(len(resultado["acumulado"]), 12)
        self.assertEqual(resultado["acumulado"][-1]["vitorias_a"], 12)

    def test_pendentes_nao_entram_nos_calculos(self):
        resultado = confronto_direto(
            [jogo(1, 1)], A, B, pendentes_entre_eles=2
        )

        self.assertEqual(resultado["pendentes_entre_eles"], 2)
        self.assertEqual(resultado["indicadores_a"]["partidas"], 1)
        self.assertEqual(resultado["indicadores_b"]["partidas"], 1)

    def test_nao_altera_entradas(self):
        linhas = [jogo(2, 2), jogo(1, 1, 1, 3)]
        original = deepcopy((linhas, A, B))

        confronto_direto(linhas, A, B)

        self.assertEqual((linhas, A, B), original)

    def test_rejeita_mesmo_atleta(self):
        with self.assertRaisesMessage(
            ValueError, "Escolha um atleta diferente"
        ):
            confronto_direto([], A, A)