from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from contas.models import Curso
from desempenho.consultas import linhas_do_atleta
from partidas.models import (
    AdversarioExterno, Contestacao, Partida, SetPartida,
)


class LinhasDoAtletaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        curso = Curso.objects.first()

        def atleta(nome, nusp):
            return get_user_model().objects.create_user(
                email=f"{nome.lower()}@usp.br",
                password="pingpoli123",
                nome=nome,
                nusp=nusp,
                curso=curso,
                ano_ingresso=2024,
            )

        cls.ana = atleta("Ana", 101)
        cls.bruno = atleta("Bruno", 102)
        cls.carla = atleta("Carla", 103)
        cls.externo = AdversarioExterno.objects.create(
            nome="Carlos", clube="ECP"
        )

    def criar_partida(self, **alteracoes):
        dados = {
            "atleta": self.ana,
            "adversario": self.bruno,
            "tipo_adversario": "poli",
            "formato": 5,
            "data_jogo": date(2026, 11, 18),
            "status": "confirmada",
        }
        dados.update(alteracoes)
        partida = Partida.objects.create(**dados)

        # Registrante vence por 3–1; pontos totais: 40–32.
        for numero, (a, b) in enumerate(
            [(11, 5), (7, 11), (11, 9), (11, 7)], start=1
        ):
            SetPartida.objects.create(
                partida=partida,
                numero=numero,
                pontos_atleta=a,
                pontos_adversario=b,
            )
        return partida

    def consultar(self, atleta=None, **filtros):
        return linhas_do_atleta(
            atleta or self.ana,
            filtros.pop("inicio", date(2026, 11, 1)),
            filtros.pop("fim", date(2026, 11, 30)),
            **filtros,
        )

    def test_perspectiva_do_registrante(self):
        partida = self.criar_partida()
        self.assertEqual(self.consultar(), [{
            "partida_id": partida.pk,
            "data": date(2026, 11, 18),
            "campeonato_id": None,
            "competicao": "Amistoso/Treino",
            "tipo_adversario": "poli",
            "adversario_id": self.bruno.pk,
            "adversario_nome": "Bruno",
            "sets_pro": 3,
            "sets_contra": 1,
            "pontos_pro": 40,
            "pontos_contra": 32,
            "venceu": True,
        }])

    def test_perspectiva_do_adversario(self):
        self.criar_partida()
        linha = self.consultar(self.bruno)[0]

        self.assertEqual(linha["adversario_id"], self.ana.pk)
        self.assertEqual(linha["adversario_nome"], "Ana")
        self.assertEqual(linha["sets_pro"], 1)
        self.assertEqual(linha["sets_contra"], 3)
        self.assertEqual(linha["pontos_pro"], 32)
        self.assertEqual(linha["pontos_contra"], 40)
        self.assertFalse(linha["venceu"])

    def test_so_confirmadas(self):
        confirmada = self.criar_partida()
        for status in ("pendente", "contestada", "removida"):
            self.criar_partida(status=status)

        self.assertEqual(
            [linha["partida_id"] for linha in self.consultar()],
            [confirmada.pk],
        )

    def test_exclui_partidas_de_outros_atletas(self):
        self.criar_partida(atleta=self.carla)
        self.assertEqual(self.consultar(), [])

    def test_adversario_externo(self):
        self.criar_partida(
            adversario=None,
            adversario_externo=self.externo,
            tipo_adversario="externo",
        )
        linha = self.consultar()[0]
        self.assertEqual(linha["tipo_adversario"], "externo")
        self.assertEqual(linha["adversario_id"], self.externo.pk)
        self.assertEqual(linha["adversario_nome"], "Carlos")

    def test_filtro_tipo_adversario(self):
        poli = self.criar_partida()
        externo = self.criar_partida(
            adversario=None,
            adversario_externo=self.externo,
            tipo_adversario="externo",
        )
        for tipo, esperado in [("poli", poli), ("externo", externo)]:
            with self.subTest(tipo=tipo):
                self.assertEqual(
                    [
                        linha["partida_id"]
                        for linha in self.consultar(tipo_adversario=tipo)
                    ],
                    [esperado.pk],
                )

    def test_periodo_inclusivo(self):
        for dia in (9, 10, 20, 21):
            self.criar_partida(data_jogo=date(2026, 11, dia))

        linhas = self.consultar(
            inicio=date(2026, 11, 10),
            fim=date(2026, 11, 20),
        )
        self.assertEqual([linha["data"].day for linha in linhas], [10, 20])

    def test_ignora_sets_propostos_em_contestacao(self):
        partida = self.criar_partida()
        contestacao = Contestacao.objects.create(
            partida=partida,
            contestante=self.bruno,
            justificativa="O placar informado estava incorreto.",
        )
        for numero in range(1, 4):
            SetPartida.objects.create(
                partida=partida,
                contestacao=contestacao,
                numero=numero,
                pontos_atleta=0,
                pontos_adversario=11,
            )

        linha = self.consultar()[0]
        self.assertEqual(
            (linha["sets_pro"], linha["sets_contra"]), (3, 1)
        )
        self.assertEqual(
            (linha["pontos_pro"], linha["pontos_contra"]), (40, 32)
        )

    def test_consultas_nao_crescem_por_partida(self):
        for _ in range(4):
            self.criar_partida()

        with self.assertNumQueries(2):
            linhas = self.consultar()
        self.assertEqual(len(linhas), 4)

    def test_filtros_invalidos(self):
        for filtros in [
            {"tipo_adversario": "invalido"},
            {"competicao": "invalida"},
            {"competicao": "0"},
            {
                "inicio": date(2026, 11, 20),
                "fim": date(2026, 11, 10),
            },
        ]:
            with self.subTest(filtros=filtros):
                with self.assertRaises(ValueError):
                    self.consultar(**filtros)

    def criar_campeonato(self, nome):
        from datetime import timedelta

        from django.utils import timezone

        from competicoes.models import Campeonato

        agora = timezone.now()
        return Campeonato.objects.create(
            nome=nome,
            organizador="Poli",
            local_campeonato="CEPEUSP",
            data_inicio=date(2026, 11, 18),
            data_fim=date(2026, 11, 19),
            abertura_inscricoes=agora - timedelta(days=20),
            encerramento_inscricoes=agora - timedelta(days=10),
            status="finalizado",
            criado_por=self.ana,
        )

    def test_filtro_campeonato_por_id(self):
        campeonato = self.criar_campeonato("Copa")
        outro = self.criar_campeonato("Outro campeonato")
        esperada = self.criar_partida(campeonato=campeonato)
        self.criar_partida(campeonato=outro)
        self.criar_partida()

        for identificador in (campeonato.pk, str(campeonato.pk)):
            with self.subTest(identificador=identificador):
                linhas = self.consultar(competicao=identificador)
                self.assertEqual(
                    [linha["partida_id"] for linha in linhas],
                    [esperada.pk],
                )
                self.assertEqual(linhas[0]["campeonato_id"], campeonato.pk)
                self.assertEqual(linhas[0]["competicao"], "Copa")

    def test_filtro_amistoso_e_todas(self):
        campeonato = self.criar_campeonato("Copa")
        self.criar_partida(campeonato=campeonato)
        amistoso = self.criar_partida()

        self.assertEqual(
            [
                linha["partida_id"]
                for linha in self.consultar(competicao="amistoso")
            ],
            [amistoso.pk],
        )
        self.assertEqual(len(self.consultar(competicao="todas")), 2)

    def test_filtros_combinados_na_perspectiva_do_adversario(self):
        campeonato = self.criar_campeonato("Copa")
        esperada = self.criar_partida(
            atleta=self.bruno,
            adversario=self.ana,
            campeonato=campeonato,
        )
        self.criar_partida()
        self.criar_partida(
            campeonato=campeonato,
            data_jogo=date(2026, 10, 18),
        )
        self.criar_partida(
            campeonato=campeonato,
            tipo_adversario="externo",
            adversario=None,
            adversario_externo=self.externo,
        )

        linhas = self.consultar(
            competicao=str(campeonato.pk),
            tipo_adversario="poli",
        )
        self.assertEqual(
            [linha["partida_id"] for linha in linhas], [esperada.pk]
        )
        self.assertEqual(linhas[0]["adversario_id"], self.bruno.pk)
        self.assertEqual(linhas[0]["sets_pro"], 1)
        self.assertFalse(linhas[0]["venceu"])