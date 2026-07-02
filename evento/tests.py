from datetime import timedelta
import calendar

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.timezone import localtime, now

from equipe.models import Equipe, Lideranca
from escala.models import Funcao, Escala
from evento.models import Evento
from evento.views_recorrente import gerar_cultos_mensais

User = get_user_model()


class EventosApiTests(TestCase):
    def test_cores_por_status_da_minha_escala(self):
        equipe = Equipe.objects.create(nome="Louvor")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        base = now() + timedelta(days=2)
        ev_conf = Evento.objects.create(
            nome="Confirmado", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        ev_pend = Evento.objects.create(
            nome="Pendente",
            data_inicio=base + timedelta(days=1),
            data_fim=base + timedelta(days=1, hours=2),
        )
        ev_outro = Evento.objects.create(
            nome="Outro",
            data_inicio=base + timedelta(days=2),
            data_fim=base + timedelta(days=2, hours=2),
        )

        user = User.objects.create_user(
            username="vol", password="x", cpf="10000003001",
            is_first_login=False, termo_aceito_em=now(),
        )
        Escala.objects.create(usuario=user, funcao=funcao, evento=ev_conf, confirmada=True)
        Escala.objects.create(usuario=user, funcao=funcao, evento=ev_pend, confirmada=False)

        self.client.force_login(user)
        resp = self.client.get(reverse('eventos_api'))
        self.assertEqual(resp.status_code, 200)

        cores = {item['title']: item['backgroundColor'] for item in resp.json()}
        self.assertEqual(cores['Confirmado'], '#2e7d32')  # verde
        self.assertEqual(cores['Pendente'], '#ef6c00')    # laranja
        self.assertEqual(cores['Outro'], '#3b5bdb')       # azul


class GerarCultosMensaisTests(TestCase):
    def test_gera_cultos_de_domingo_e_quarta_no_mes(self):
        eventos_criados, eventos_pulados = gerar_cultos_mensais(
            ano=2026,
            mes=6,
            quantidade_meses=1,
        )

        self.assertEqual(len(eventos_criados), 12)
        self.assertEqual(eventos_pulados, 0)

        culto_manha = Evento.objects.get(
            nome="Culto de Domingo - Manhã",
            data_inicio__date="2026-06-14",
        )
        self.assertEqual(localtime(culto_manha.data_inicio).strftime("%H:%M"), "09:45")
        self.assertEqual(localtime(culto_manha.data_fim).strftime("%H:%M"), "12:00")

        culto_noite = Evento.objects.get(
            nome="Culto de Domingo - Noite",
            data_inicio__date="2026-06-14",
        )
        self.assertEqual(localtime(culto_noite.data_inicio).strftime("%H:%M"), "18:00")
        self.assertEqual(localtime(culto_noite.data_fim).strftime("%H:%M"), "21:00")

        culto_quarta = Evento.objects.get(
            nome="Culto de Quarta-feira",
            data_inicio__date="2026-06-17",
        )
        self.assertEqual(localtime(culto_quarta.data_inicio).strftime("%H:%M"), "19:30")
        self.assertEqual(localtime(culto_quarta.data_fim).strftime("%H:%M"), "21:00")

    def test_nao_duplica_eventos_existentes_por_padrao(self):
        gerar_cultos_mensais(ano=2026, mes=6, quantidade_meses=1)
        eventos_criados, eventos_pulados = gerar_cultos_mensais(
            ano=2026,
            mes=6,
            quantidade_meses=1,
        )

        self.assertEqual(len(eventos_criados), 0)
        self.assertEqual(eventos_pulados, 12)
        self.assertEqual(Evento.objects.count(), 12)

    def test_apenas_admin_acessa_tela_de_geracao(self):
        usuario_comum = User.objects.create_user(
            username="membro",
            password="x",
            cpf="10000003002",
            is_first_login=False,
            termo_aceito_em=now(),
        )
        admin = User.objects.create_user(
            username="admin",
            password="x",
            cpf="10000003003",
            is_staff=True,
            is_first_login=False,
            termo_aceito_em=now(),
        )

        self.client.force_login(usuario_comum)
        resp = self.client.get(reverse('gerar_cultos_mensais'))
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(admin)
        resp = self.client.get(reverse('gerar_cultos_mensais'))
        self.assertEqual(resp.status_code, 200)


class GerarEventosEmMassaTests(TestCase):
    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Recepção")
        self.lider = User.objects.create_user(
            username="lider_massa", password="x", cpf="10000003004",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)
        self.client.force_login(self.lider)

    def test_lider_gera_dias_escolhidos_apenas_no_proximo_mes(self):
        hoje = now().date()
        proximo_mes = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1)
        mes_valor = proximo_mes.strftime('%Y-%m')
        segundas = sum(
            1 for dia in range(1, calendar.monthrange(proximo_mes.year, proximo_mes.month)[1] + 1)
            if proximo_mes.replace(day=dia).weekday() == 0
        )

        resp = self.client.post(reverse('gerar_eventos_em_massa'), {
            'nome': 'Reunião semanal',
            'equipe': self.equipe.pk,
            'mes': mes_valor,
            'dias_da_semana': ['0'],
            'horario_inicio': '19:00',
            'horario_fim': '21:00',
            'observacao': 'Gerado em massa',
        })

        self.assertRedirects(resp, reverse('evento_list'))
        eventos = Evento.objects.filter(nome='Reunião semanal')
        self.assertEqual(eventos.count(), segundas)
        self.assertTrue(all(evento.equipe == self.equipe for evento in eventos))
        self.assertTrue(all(localtime(evento.data_inicio).weekday() == 0 for evento in eventos))
        self.assertTrue(all(localtime(evento.data_inicio).month == proximo_mes.month for evento in eventos))

    def test_rejeita_mes_alem_do_proximo(self):
        hoje = now().date()
        mes_futuro = (hoje.replace(day=28) + timedelta(days=40)).replace(day=1)

        resp = self.client.post(reverse('gerar_eventos_em_massa'), {
            'nome': 'Evento distante',
            'equipe': self.equipe.pk,
            'mes': mes_futuro.strftime('%Y-%m'),
            'dias_da_semana': ['2'],
            'horario_inicio': '19:00',
            'horario_fim': '21:00',
        })

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Evento.objects.filter(nome='Evento distante').exists())
        self.assertIn('mes', resp.context['form'].errors)

    def test_lider_nao_pode_gerar_para_outra_equipe(self):
        outra_equipe = Equipe.objects.create(nome="Louvor")
        hoje = now().date()

        resp = self.client.post(reverse('gerar_eventos_em_massa'), {
            'nome': 'Evento indevido',
            'equipe': outra_equipe.pk,
            'mes': hoje.strftime('%Y-%m'),
            'dias_da_semana': ['4'],
            'horario_inicio': '19:00',
            'horario_fim': '21:00',
        })

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Evento.objects.filter(nome='Evento indevido').exists())
