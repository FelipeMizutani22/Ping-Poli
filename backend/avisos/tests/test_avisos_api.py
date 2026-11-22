"""Testes da API de avisos (UC05, UC06 · C1)."""
from datetime import timedelta

from django.core import mail
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from avisos.models import Aviso, AvisoLeitura
from nucleo.models import Notificacao
from partidas.tests.test_partidas_api import criar_atleta

URL = "/api/v1/avisos/"


class BaseAvisos(APITestCase):
    def setUp(self):
        self.ana = criar_atleta("ana@usp.br", "Ana Lima", 1001)
        self.bruno = criar_atleta("bruno@usp.br", "Bruno Kato", 1002)
        self.pendente = criar_atleta("paulo@usp.br", "Paulo Novo", 1003, situacao="pendente")
        self.marina = criar_atleta("marina@usp.br", "Marina Diretora", 1004, papel="diretor")
        self.entrar(self.marina)

    def entrar(self, atleta):
        token, _ = Token.objects.get_or_create(user=atleta)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def aviso(self, titulo="Treino extra", **campos):
        campos.setdefault("conteudo", "Treino extra no sábado às 10h no CEPEUSP.")
        return Aviso.objects.create(autor=self.marina, titulo=titulo, **campos)

    def dados(self, **mudancas):
        base = {"titulo": "Treino extra", "conteudo": "Treino extra no sábado às 10h.", "categoria": "treino"}
        base.update(mudancas)
        return base


class ListarAvisosTests(BaseAvisos):
    def test_fixados_primeiro_depois_mais_recentes(self):
        agora = timezone.now()
        antigo = self.aviso("Antigo", data_publicacao=agora - timedelta(days=3))
        recente = self.aviso("Recente", data_publicacao=agora - timedelta(days=1))
        fixado = self.aviso("Fixado", fixado=True, data_publicacao=agora - timedelta(days=5))
        self.entrar(self.ana)
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([a["id"] for a in r.data], [fixado.id, recente.id, antigo.id])

    def test_formato_do_aviso(self):
        self.aviso(conteudo="x" * 300)
        self.entrar(self.ana)
        item = self.client.get(URL).data[0]
        self.assertEqual(len(item["trecho"]), 200)
        self.assertEqual(item["autor"], {"id": self.marina.id, "nome": "Marina Diretora", "nusp": 1004})
        self.assertFalse(item["lido"])
        self.assertNotIn("expirado", item)

    def test_atleta_nao_ve_excluidos_nem_expirados(self):
        self.aviso("Vigente")
        self.aviso("Vence hoje", data_expiracao=timezone.localdate())
        self.aviso("Expirado", data_expiracao=timezone.localdate() - timedelta(days=1))
        self.aviso("Excluído", excluido=True)
        self.entrar(self.ana)
        titulos = {a["titulo"] for a in self.client.get(URL).data}
        self.assertEqual(titulos, {"Vigente", "Vence hoje"})

    def test_diretor_ve_expirados_marcados(self):
        self.aviso("Expirado", data_expiracao=timezone.localdate() - timedelta(days=1))
        self.aviso("Excluído", excluido=True)
        r = self.client.get(URL)
        self.assertEqual(len(r.data), 1)
        self.assertTrue(r.data[0]["expirado"])

    def test_filtro_por_categoria(self):
        self.aviso("Geral", categoria="geral")
        self.aviso("Urgente", categoria="urgente")
        r = self.client.get(URL, {"categoria": "urgente"})
        self.assertEqual([a["titulo"] for a in r.data], ["Urgente"])

    def test_conta_nao_ativa_e_anonimo(self):
        self.entrar(self.pendente)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)


class DetalheELeituraTests(BaseAvisos):
    def test_abrir_aviso_registra_leitura_uma_vez(self):
        aviso = self.aviso()
        self.entrar(self.ana)
        r = self.client.get(f"{URL}{aviso.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["lido"])
        self.client.get(f"{URL}{aviso.id}/")
        self.assertEqual(AvisoLeitura.objects.filter(aviso=aviso, atleta=self.ana).count(), 1)
        self.assertIn(self.ana, aviso.leitores.all())
        # "Novo" é por atleta: o Bruno ainda não leu
        self.entrar(self.bruno)
        self.assertFalse(self.client.get(URL).data[0]["lido"])

    def test_aviso_excluido_ou_expirado_da_404_para_atleta(self):
        excluido = self.aviso(excluido=True)
        expirado = self.aviso(data_expiracao=timezone.localdate() - timedelta(days=1))
        self.entrar(self.ana)
        for aviso in (excluido, expirado):
            r = self.client.get(f"{URL}{aviso.id}/")
            self.assertEqual(r.status_code, 404)
            self.assertEqual(r.data["detail"], "Este aviso não está mais disponível")
        self.assertFalse(AvisoLeitura.objects.exists())


class PublicarAvisoTests(BaseAvisos):
    def test_diretor_publica(self):
        r = self.client.post(URL, self.dados(), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        aviso = Aviso.objects.get(pk=r.data["id"])
        self.assertEqual(aviso.autor, self.marina)
        self.assertFalse(aviso.fixado)
        self.assertEqual(r.data["autor"]["id"], self.marina.id)

    def test_atleta_nao_publica(self):
        self.entrar(self.ana)
        self.assertEqual(self.client.post(URL, self.dados(), format="json").status_code, 403)
        self.assertFalse(Aviso.objects.exists())

    def test_validacao_dos_campos(self):
        r = self.client.post(URL, self.dados(titulo="ab", conteudo="curto", categoria="festa"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {"titulo", "conteudo", "categoria"})

    def test_expiracao_no_passado(self):
        ontem = (timezone.localdate() - timedelta(days=1)).isoformat()
        r = self.client.post(URL, self.dados(data_expiracao=ontem), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["data_expiracao"], ["A data de expiração deve ser hoje ou uma data futura"])

    def test_quarto_fixado_da_409(self):
        for i in range(3):
            self.aviso(f"Fixado {i}", fixado=True)
        self.aviso("Fixado e excluído", fixado=True, excluido=True)   # não conta
        r = self.client.post(URL, self.dados(fixado=True), format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["codigo"], "limite_fixados")
        self.assertEqual(r.data["detail"], "Já existem 3 avisos fixados. Desafixe um deles antes de continuar")
        self.assertEqual(Aviso.objects.count(), 4)

    def test_urgente_notifica_atletas_ativos(self):
        r = self.client.post(URL, self.dados(categoria="urgente"), format="json")
        self.assertEqual(r.status_code, 201)
        destinatarios = set(Notificacao.objects.filter(tipo="aviso_novo").values_list("destinatario", flat=True))
        self.assertEqual(destinatarios, {self.ana.id, self.bruno.id, self.marina.id})

    def test_aviso_comum_nao_notifica(self):
        self.client.post(URL, self.dados(), format="json")
        self.assertFalse(Notificacao.objects.exists())

    def test_notificar_por_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(URL, self.dados(notificar_email=True), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("notificar_email", r.data)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["ana@usp.br", "bruno@usp.br", "marina@usp.br"])


class EditarExcluirFixarTests(BaseAvisos):
    def test_editar_grava_data_de_edicao(self):
        aviso = self.aviso()
        r = self.client.patch(f"{URL}{aviso.id}/", {"titulo": "Treino cancelado"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["titulo"], "Treino cancelado")
        self.assertIsNotNone(r.data["data_edicao"])

    def test_atleta_nao_edita_nem_exclui(self):
        aviso = self.aviso()
        self.entrar(self.ana)
        self.assertEqual(self.client.patch(f"{URL}{aviso.id}/", {"titulo": "Hack"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"{URL}{aviso.id}/").status_code, 403)
        self.assertEqual(self.client.post(f"{URL}{aviso.id}/fixar/").status_code, 403)

    def test_editar_para_fixado_respeita_limite(self):
        for i in range(3):
            self.aviso(f"Fixado {i}", fixado=True)
        aviso = self.aviso()
        r = self.client.patch(f"{URL}{aviso.id}/", {"fixado": True}, format="json")
        self.assertEqual(r.status_code, 409)
        aviso.refresh_from_db()
        self.assertFalse(aviso.fixado)

    def test_editar_um_ja_fixado_com_limite_cheio(self):
        fixados = [self.aviso(f"Fixado {i}", fixado=True) for i in range(3)]
        r = self.client.patch(f"{URL}{fixados[0].id}/", {"fixado": True, "titulo": "Novo título"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_excluir_e_logico(self):
        aviso = self.aviso()
        self.assertEqual(self.client.delete(f"{URL}{aviso.id}/").status_code, 204)
        aviso.refresh_from_db()
        self.assertTrue(aviso.excluido)
        self.assertEqual(self.client.get(URL).data, [])
        self.assertEqual(self.client.delete(f"{URL}{aviso.id}/").status_code, 404)

    def test_fixar_alterna(self):
        aviso = self.aviso()
        r = self.client.post(f"{URL}{aviso.id}/fixar/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["fixado"])
        r = self.client.post(f"{URL}{aviso.id}/fixar/")
        self.assertFalse(r.data["fixado"])

    def test_fixar_quarto_da_409_e_desafixar_libera(self):
        fixados = [self.aviso(f"Fixado {i}", fixado=True) for i in range(3)]
        aviso = self.aviso()
        r = self.client.post(f"{URL}{aviso.id}/fixar/")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["codigo"], "limite_fixados")
        self.client.post(f"{URL}{fixados[0].id}/fixar/")
        self.assertEqual(self.client.post(f"{URL}{aviso.id}/fixar/").status_code, 200)

    def test_fixar_excluido_da_404(self):
        aviso = self.aviso(excluido=True)
        self.assertEqual(self.client.post(f"{URL}{aviso.id}/fixar/").status_code, 404)
