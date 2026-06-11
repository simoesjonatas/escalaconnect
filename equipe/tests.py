from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from equipe.models import Equipe, Lideranca, MembrosEquipe
from evento.models import Evento
from escala.models import Funcao, Escala
from disponivel.models import Disponivel

User = get_user_model()


class DashboardLiderTests(TestCase):
    def test_dashboard_acessivel_para_lider_onboarded(self):
        equipe = Equipe.objects.create(nome="Louvor")
        lider = User.objects.create_user(
            username="lider",
            password="senha-teste",
            cpf="10000000500",
            is_first_login=False,      # passa pelo FirstLoginMiddleware
            termo_aceito_em=now(),     # passa pelo TermoVoluntarioMiddleware
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'equipe/dashboard_lider.html')

    def test_dashboard_mostra_disponiveis_nos_buracos(self):
        equipe = Equipe.objects.create(nome="Mídia")
        funcao = Funcao.objects.create(nome="Projeção", equipe=equipe)
        base = (now() + timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0)
        evento = Evento.objects.create(
            nome="Culto", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        Escala.objects.create(funcao=funcao, evento=evento)  # vaga em aberto

        vol = User.objects.create_user(
            username="voluntario_d", password="x", cpf="10000002001",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=vol, aprovado=True)
        Disponivel.objects.create(
            usuario=vol,
            data_inicio=base - timedelta(hours=1),
            data_fim=base + timedelta(hours=3),
        )

        lider = User.objects.create_user(
            username="lider2", password="x", cpf="10000002002",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "voluntario_d")  # o disponível aparece na coluna do painel


class HomeAvisoMembrosPendentesTests(TestCase):
    def test_lider_ve_aviso_de_pedido_de_entrada(self):
        equipe = Equipe.objects.create(nome="Diaconia")
        lider = User.objects.create_user(
            username="lid", password="x", cpf="10000005001",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        cand = User.objects.create_user(
            username="cand", password="x", cpf="10000005002",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=cand, aprovado=False)

        self.client.force_login(lider)
        resp = self.client.get('/')
        self.assertContains(resp, "querendo entrar nas suas equipes")
        self.assertContains(resp, "Diaconia")
