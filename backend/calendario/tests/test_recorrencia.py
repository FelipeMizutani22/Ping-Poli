"""Testes dos treinos recorrentes semanais (UC07 · C11)."""
from datetime import date, timedelta

from django.core import mail

from calendario.models import Evento
from calendario.serializers import _somar_meses
from calendario.tests.test_calendario_api import HOJE, BaseCalendario
from nucleo.models import Notificacao

URL = "/api/v1/eventos/"


class RecorrenciaTests(BaseCalendario):
    def criar_serie(self, semanas=4, **extra):
        inicio = HOJE() + timedelta(days=1)
        dados = self.dados(data_evento=inicio.isoformat(), recorrencia="semanal",
                           repetir_ate=(inicio + timedelta(weeks=semanas - 1)).isoformat(), **extra)
        r = self.client.post(URL, dados, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r, list(Evento.objects.filter(serie_id=r.data["serie_id"]).order_by("data_evento"))

    def test_cria_uma_ocorrencia_por_semana_na_mesma_serie(self):
        r, serie = self.criar_serie(semanas=4)
        self.assertEqual(r.data["ocorrencias"], 4)
        self.assertEqual(r.data["serie_id"], r.data["id"])   # a série leva o id da primeira ocorrência
        datas = [e.data_evento for e in serie]
        self.assertEqual([(b - a).days for a, b in zip(datas, datas[1:])], [7, 7, 7])
        self.assertTrue(all(e.hora_inicio == serie[0].hora_inicio and e.criado_por == self.marina for e in serie))

    def test_sem_recorrencia_nao_tem_serie(self):
        r = self.client.post(URL, self.dados(), format="json")
        self.assertIsNone(r.data["serie_id"])
        self.assertEqual(r.data["ocorrencias"], 1)

    def test_limite_de_27_ocorrencias(self):
        inicio = HOJE() + timedelta(days=1)
        ate = _somar_meses(inicio, 6)   # ~26 semanas: cabe tudo, mas nunca mais que 27
        r = self.client.post(URL, self.dados(data_evento=inicio.isoformat(), recorrencia="semanal",
                                             repetir_ate=ate.isoformat()), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertLessEqual(r.data["ocorrencias"], 27)
        self.assertGreaterEqual(r.data["ocorrencias"], 26)

    def test_validacoes_da_recorrencia(self):
        dia = HOJE() + timedelta(days=1)
        casos = [
            ({"recorrencia": "semanal"}, "Informe até quando o evento se repete"),
            ({"recorrencia": "semanal", "repetir_ate": dia.isoformat()},
             "A data final da recorrência deve ser posterior à data do evento"),
            ({"recorrencia": "semanal", "repetir_ate": (_somar_meses(dia, 6) + timedelta(days=1)).isoformat()},
             "A recorrência pode ir no máximo até 6 meses depois da data do evento"),
        ]
        for extra, mensagem in casos:
            with self.subTest(extra=extra):
                r = self.client.post(URL, self.dados(data_evento=dia.isoformat(), **extra), format="json")
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.data["repetir_ate"], [mensagem])
        self.assertFalse(Evento.objects.exists())

    def test_somar_meses_no_fim_do_mes(self):
        self.assertEqual(_somar_meses(date(2026, 8, 31), 6), date(2027, 2, 28))

    def test_editar_somente_esta(self):
        _, serie = self.criar_serie()
        r = self.client.patch(f"{URL}{serie[1].id}/", {"local_evento": "Ginásio 2"}, format="json")
        self.assertEqual(r.status_code, 200)
        locais = list(Evento.objects.filter(serie_id=serie[0].serie_id).order_by("data_evento")
                      .values_list("local_evento", flat=True))
        self.assertEqual(locais, ["CEPEUSP – Ginásio", "Ginásio 2", "CEPEUSP – Ginásio", "CEPEUSP – Ginásio"])

    def test_editar_esta_e_as_seguintes_manda_um_email(self):
        _, serie = self.criar_serie()
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.patch(f"{URL}{serie[1].id}/", {"hora_inicio": "19:00", "hora_fim": "21:00",
                                                           "alcance": "seguintes"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        horas = [e.hora_inicio.hour for e in Evento.objects.filter(serie_id=serie[0].serie_id).order_by("data_evento")]
        self.assertEqual(horas, [18, 19, 19, 19])
        self.assertEqual(len(mail.outbox), 3)   # um e-mail por atleta ativo, não um por ocorrência

    def test_seguintes_com_o_formulario_inteiro_mantem_as_datas(self):
        _, serie = self.criar_serie()
        form = {"tipo": "treino", "titulo": "Treino técnico", "data_evento": serie[1].data_evento.isoformat(),
                "hora_inicio": "09:00", "hora_fim": "11:00", "local_evento": "CEPEUSP – Ginásio", "descricao": "",
                "alcance": "seguintes"}
        r = self.client.patch(f"{URL}{serie[1].id}/", form, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        depois = list(Evento.objects.filter(serie_id=serie[0].serie_id).order_by("data_evento"))
        self.assertEqual([e.data_evento for e in depois], [e.data_evento for e in serie])
        self.assertEqual([e.hora_inicio.hour for e in depois], [18, 9, 9, 9])

    def test_nao_muda_a_data_de_varias_de_uma_vez(self):
        _, serie = self.criar_serie()
        nova = (serie[1].data_evento + timedelta(days=1)).isoformat()
        r = self.client.patch(f"{URL}{serie[1].id}/", {"data_evento": nova, "alcance": "seguintes"}, format="json")
        self.assertEqual(r.data, {"data_evento": ["Para mudar a data, edite somente esta ocorrência"]})
        r = self.client.patch(f"{URL}{serie[1].id}/", {"data_evento": nova}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_cancelar_esta_e_as_seguintes(self):
        _, serie = self.criar_serie()
        serie[2].status = "cancelado"   # já cancelada antes: fica como está
        serie[2].motivo_cancelamento = "Feriado"
        serie[2].save()
        r = self.client.post(f"{URL}{serie[1].id}/cancelar/", {"motivo": "Reforma do ginásio", "alcance": "seguintes"},
                             format="json")
        self.assertEqual(r.status_code, 200)
        eventos = list(Evento.objects.filter(serie_id=serie[0].serie_id).order_by("data_evento"))
        self.assertEqual([e.status for e in eventos], ["agendado", "cancelado", "cancelado", "cancelado"])
        self.assertEqual([e.motivo_cancelamento for e in eventos][1:], ["Reforma do ginásio", "Feriado", "Reforma do ginásio"])
        self.assertEqual(Notificacao.objects.filter(tipo="evento_cancelado").count(), 3)   # uma por atleta
        self.assertIn("2 ocorrências", Notificacao.objects.first().mensagem)   # a já cancelada não conta

    def test_cancelar_somente_esta(self):
        _, serie = self.criar_serie()
        self.client.post(f"{URL}{serie[0].id}/cancelar/", {}, format="json")
        status = list(Evento.objects.filter(serie_id=serie[0].serie_id).values_list("status", flat=True))
        self.assertEqual(status.count("cancelado"), 1)
