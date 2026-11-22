import random

from django.test import SimpleTestCase

from partidas.regras import gerar_placar_aleatorio, resultado, sets_para_vencer, validar_placar, validar_set

def S(pontos_atleta, pontos_adversario):
    """Atalho para montar um set no formato do contrato da API."""
    return {"pontos_atleta": pontos_atleta, "pontos_adversario": pontos_adversario}


class ValidarSetTests(SimpleTestCase):
    def test_sets_validos(self):
        for a, b in [(11, 0), (11, 9), (12, 10), (15, 13), (0, 11), (9, 11), (10, 12), (13, 15)]:
            with self.subTest(placar=f"{a}-{b}"):
                self.assertEqual(validar_set(a, b, 1), [])

    def test_sem_11_pontos_ou_sem_2_de_vantagem(self):
        for a, b in [(11, 10), (10, 8), (10, 11), (5, 3)]:
            with self.subTest(placar=f"{a}-{b}"):
                self.assertEqual(
                    validar_set(a, b, 2),
                    ["Set 2: o vencedor precisa de 11 pontos com 2 de vantagem"],
                )

    def test_prorrogacao_com_diferenca_diferente_de_2(self):
        for a, b in [(12, 9), (15, 11), (9, 12)]:
            with self.subTest(placar=f"{a}-{b}"):
                self.assertEqual(
                    validar_set(a, b, 3),
                    ["Set 3: acima de 11 pontos, a diferença deve ser exatamente 2"],
                )

    def test_set_empatado(self):
        self.assertEqual(validar_set(11, 11, 1), ["Set 1: o set não pode terminar empatado"])

    def test_pontos_fora_da_faixa(self):
        for a, b in [(-1, 11), (100, 98)]:
            with self.subTest(placar=f"{a}-{b}"):
                self.assertEqual(validar_set(a, b, 4), ["Set 4: os pontos devem estar entre 0 e 99"])


class ValidarPlacarTests(SimpleTestCase):
    def test_sets_para_vencer(self):
        self.assertEqual(sets_para_vencer(3), 2)
        self.assertEqual(sets_para_vencer(5), 3)
        self.assertEqual(sets_para_vencer(7), 4)

    def test_placares_validos(self):
        casos = [
            ([S(11, 5), S(11, 7)], 3),
            ([S(11, 5), S(9, 11), S(11, 7)], 3),
            ([S(11, 5), S(9, 11), S(11, 7), S(12, 10)], 5),
            ([S(5, 11), S(11, 9), S(9, 11), S(11, 8), S(13, 15)], 5),
            ([S(11, 1), S(11, 2), S(11, 3), S(11, 4)], 7),
        ]
        for sets, formato in casos:
            with self.subTest(sets=sets, formato=formato):
                self.assertEqual(validar_placar(sets, formato), [])

    def test_set_depois_do_fim(self):
        self.assertEqual(
            validar_placar([S(11, 5), S(11, 5), S(11, 5), S(11, 5)], 5),
            ["A partida já estava decidida no set 3"],
        )

    def test_sem_vencedor(self):
        self.assertEqual(
            validar_placar([S(11, 5), S(5, 11)], 5),
            ["Nenhum jogador venceu 3 sets (melhor de 5)"],
        )

    def test_lista_vazia(self):
        self.assertEqual(validar_placar([], 3), ["Nenhum jogador venceu 2 sets (melhor de 3)"])

    def test_sets_demais(self):
        self.assertEqual(
            validar_placar([S(11, 5)] * 4, 3),
            ["Melhor de 3 admite no máximo 3 sets"],
        )

    def test_exemplo_do_uc15_11x10_no_set_2(self):
        self.assertEqual(
            validar_placar([S(11, 5), S(11, 10), S(11, 7)], 3),
            ["Set 2: o vencedor precisa de 11 pontos com 2 de vantagem"],
        )

    def test_devolve_todos_os_erros_de_set(self):
        self.assertEqual(
            validar_placar([S(11, 10), S(11, 5), S(11, 11)], 5),
            [
                "Set 1: o vencedor precisa de 11 pontos com 2 de vantagem",
                "Set 3: o set não pode terminar empatado",
            ],
        )


class ResultadoTests(SimpleTestCase):
    def test_vitoria_do_atleta(self):
        self.assertEqual(
            resultado([S(11, 5), S(9, 11), S(11, 7), S(11, 3)]),
            {"sets_atleta": 3, "sets_adversario": 1, "vencedor": "atleta",
             "pontos_atleta": 42, "pontos_adversario": 26},
        )

    def test_vitoria_do_adversario(self):
        r = resultado([S(5, 11), S(10, 12)])
        self.assertEqual(r["vencedor"], "adversario")
        self.assertEqual((r["sets_atleta"], r["sets_adversario"]), (0, 2))
        self.assertEqual((r["pontos_atleta"], r["pontos_adversario"]), (15, 23))


class GerarPlacarAleatorioTests(SimpleTestCase):
    def test_1000_placares_sao_todos_validos(self):
        rng = random.Random(2026)
        for i in range(1000):
            formato = rng.choice([3, 5, 7])
            vence_atleta = rng.random() < 0.5
            sets = gerar_placar_aleatorio(formato, rng, vence_atleta)
            with self.subTest(i=i, formato=formato, sets=sets):
                self.assertEqual(validar_placar(sets, formato), [])
                esperado = "atleta" if vence_atleta else "adversario"
                self.assertEqual(resultado(sets)["vencedor"], esperado)

    def test_mesma_semente_gera_o_mesmo_placar(self):
        a = gerar_placar_aleatorio(5, random.Random(7), True)
        b = gerar_placar_aleatorio(5, random.Random(7), True)
        self.assertEqual(a, b)

    def test_gera_partidas_de_todos_os_tamanhos(self):
        rng = random.Random(1)
        tamanhos = {len(gerar_placar_aleatorio(5, rng, True)) for _ in range(200)}
        self.assertEqual(tamanhos, {3, 4, 5})