"""Testes da API de registro e listagem de partidas (UC15 · B2)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from competicoes.models import Campeonato, Categoria
from contas.models import Curso
from nucleo.models import Notificacao
from partidas.models import AdversarioExterno, Partida

URL = "/api/v1/partidas/"


def criar_atleta(email, nome, nusp, situacao="ativa", papel="atleta"):
    return get_user_model().objects.create_user(
        email, "pingpoli123", nome=nome, nusp=nusp, curso=Curso.objects.first(),
        ano_ingresso=2024, situacao=situacao, papel=papel,
    )


def S(a, b):
    return {"pontos_atleta": a, "pontos_adversario": b}


class BasePartidas(APITestCase):
    def setUp(self):
        self.ana = criar_atleta("ana@usp.br", "Ana Lima", 1001)
        self.bruno = criar_atleta("bruno@usp.br", "Bruno Kato", 1002)
        self.carla = criar_atleta("carla@usp.br", "Carla Dias", 1003)
        self.marina = criar_atleta("marina@usp.br", "Marina Diretora", 1004, papel="diretor")
        self.externo = AdversarioExterno.objects.create(nome="Carlos Pereira", clube="ECP")
        agora = timezone.now()
        self.copa = Campeonato.objects.create(
            nome="Copa Poli", organizador="Poli", local_campeonato="CEPEUSP",
            data_inicio=timezone.localdate(), data_fim=timezone.localdate(),
            abertura_inscricoes=agora - timedelta(days=10), encerramento_inscricoes=agora - timedelta(days=5),
            criado_por=self.marina,
        )
        self.cat_a = Categoria.objects.create(campeonato=self.copa, nome="Masculino A")
        self.entrar(self.ana)

    def entrar(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def dados(self, **mudancas):
        base = {
            "data_jogo": str(timezone.localdate()), "campeonato": None, "categoria": None, "fase": "",
            "tipo_adversario": "poli", "adversario": self.bruno.id, "adversario_externo": None,
            "formato": 5, "sets": [S(11, 7), S(9, 11), S(11, 5), S(11, 8)], "observacoes": "",
        }
        base.update(mudancas)
        return base

    def registrar(self, **mudancas):
        return self.client.post(URL, self.dados(**mudancas), format="json")


class RegistrarPartidaTests(BasePartidas):
    def test_contra_atleta_poli_nasce_pendente_e_notifica(self):
        r = self.registrar()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["status"], "pendente")
        self.assertEqual(r.data["placar_sets"], {"atleta": 3, "adversario": 1})
        self.assertEqual(r.data["vencedor"], "atleta")
        self.assertEqual(r.data["dias_para_responder"], 7)
        self.assertEqual(r.data["competicao"]["nome"], "Amistoso/Treino")
        self.assertEqual([s["numero"] for s in r.data["sets"]], [1, 2, 3, 4])
        self.assertEqual(r.data["adversario"], {"id": self.bruno.id, "nome": "Bruno Kato", "nusp": 1002})
        n = Notificacao.objects.get(destinatario=self.bruno)
        self.assertEqual((n.tipo, n.link), ("partida_pendente", "/partidas/pendentes"))

    def test_contra_externo_ja_nasce_confirmada(self):
        r = self.registrar(tipo_adversario="externo", adversario=None, adversario_externo=self.externo.id)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["status"], "confirmada")
        self.assertIsNotNone(r.data["data_confirmacao"])
        self.assertIsNone(r.data["dias_para_responder"])
        self.assertEqual(r.data["adversario_externo"]["nome"], "Carlos Pereira")
        self.assertFalse(Notificacao.objects.exists())

    def test_11x10_no_set_2_e_recusado_com_a_mensagem_do_uc(self):
        r = self.registrar(sets=[S(11, 7), S(11, 10), S(11, 5), S(11, 8)])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["sets"], ["Set 2: o vencedor precisa de 11 pontos com 2 de vantagem"])
        self.assertFalse(Partida.objects.exists())

    def test_set_depois_do_fim_e_recusado(self):
        r = self.registrar(formato=3, sets=[S(11, 7), S(11, 5), S(11, 8)])
        self.assertEqual(r.data["sets"], ["A partida já estava decidida no set 2"])

    def test_data_futura(self):
        amanha = timezone.localdate() + timedelta(days=1)
        r = self.registrar(data_jogo=str(amanha))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["data_jogo"], ["A data da partida não pode ser futura"])

    def test_nao_pode_jogar_contra_si_mesmo(self):
        r = self.registrar(adversario=self.ana.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn("adversario", r.data)

    def test_adversario_precisa_estar_ativo(self):
        igor = criar_atleta("igor@usp.br", "Igor Pereira", 1005, situacao="inativa")
        r = self.registrar(adversario=igor.id)
        self.assertEqual(r.data["adversario"], ["O adversário precisa ser um atleta com conta ativa"])

    def test_poli_sem_adversario(self):
        r = self.registrar(adversario=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn("adversario", r.data)

    def test_externo_sem_adversario_externo(self):
        r = self.registrar(tipo_adversario="externo", adversario=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn("adversario_externo", r.data)

    def test_categoria_de_outro_campeonato(self):
        outro = Campeonato.objects.create(
            nome="Open SP", organizador="FPTM", local_campeonato="SP",
            data_inicio=self.copa.data_inicio, data_fim=self.copa.data_fim,
            abertura_inscricoes=self.copa.abertura_inscricoes,
            encerramento_inscricoes=self.copa.encerramento_inscricoes, criado_por=self.marina,
        )
        r = self.registrar(campeonato=outro.id, categoria=self.cat_a.id)
        self.assertEqual(r.data["categoria"], ["A categoria não pertence ao campeonato escolhido"])

    def test_com_campeonato_e_categoria(self):
        r = self.registrar(campeonato=self.copa.id, categoria=self.cat_a.id, fase="Oitavas")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["competicao"], {"tipo": "campeonato", "campeonato_id": self.copa.id, "nome": "Copa Poli"})
        self.assertEqual(r.data["categoria"], {"id": self.cat_a.id, "nome": "Masculino A"})

    def test_sem_login_da_401(self):
        self.client.credentials()
        self.assertEqual(self.registrar().status_code, 401)


class ListarPartidasTests(BasePartidas):
    def setUp(self):
        super().setUp()
        self.p1 = self.registrar().data["id"]                                    # Ana × Bruno, pendente
        self.entrar(self.carla)
        self.p2 = self.registrar(adversario=self.ana.id).data["id"]              # Carla × Ana, pendente
        self.p3 = self.registrar(adversario=self.bruno.id).data["id"]            # Carla × Bruno
        Partida.objects.filter(pk=self.p3).update(status="contestada")
        self.entrar(self.ana)

    def ids(self, **params):
        r = self.client.get(URL, params)
        self.assertEqual(r.status_code, 200, r.data)
        return sorted(p["id"] for p in r.data)

    def test_minhas_inclui_as_que_registrei_e_as_contra_mim(self):
        self.assertEqual(self.ids(), sorted([self.p1, self.p2]))

    def test_minhas_nao_mostra_removidas(self):
        Partida.objects.filter(pk=self.p1).update(status="removida")
        self.assertEqual(self.ids(), [self.p2])

    def test_pendentes_so_as_que_esperam_a_minha_resposta(self):
        self.assertEqual(self.ids(escopo="pendentes"), [self.p2])

    def test_contestadas_e_todas_so_para_diretor(self):
        self.assertEqual(self.client.get(URL, {"escopo": "contestadas"}).status_code, 403)
        self.assertEqual(self.client.get(URL, {"escopo": "todas"}).status_code, 403)
        self.entrar(self.marina)
        self.assertEqual(self.ids(escopo="contestadas"), [self.p3])
        self.assertEqual(self.ids(escopo="todas"), sorted([self.p1, self.p2, self.p3]))
        self.assertEqual(self.ids(escopo="todas", atleta=self.bruno.id), sorted([self.p1, self.p3]))

    def test_escopo_invalido(self):
        self.assertEqual(self.client.get(URL, {"escopo": "xyz"}).status_code, 400)

    def test_detalhe_para_jogador_e_diretor_mas_nao_para_terceiros(self):
        self.assertEqual(self.client.get(f"{URL}{self.p1}/").status_code, 200)
        self.entrar(self.carla)
        self.assertEqual(self.client.get(f"{URL}{self.p1}/").status_code, 404)
        self.entrar(self.marina)
        self.assertEqual(self.client.get(f"{URL}{self.p1}/").status_code, 200)

    def test_dias_para_responder_diminui_com_o_tempo(self):
        Partida.objects.filter(pk=self.p2).update(data_registro=timezone.now() - timedelta(days=5))
        r = self.client.get(f"{URL}{self.p2}/")
        self.assertEqual(r.data["dias_para_responder"], 2)
