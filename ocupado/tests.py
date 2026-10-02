from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Equipe
from evento.models import Evento
from ocupado.models import Ocupado

User = get_user_model()


def criar_voluntario(username, cpf):
    return User.objects.create_user(
        username=username, password='x', cpf=cpf, email=f'{username}@example.com',
        is_first_login=False, termo_aceito_em=timezone.now(),
    )


class IndisponibilidadeNoSiteTests(TestCase):
    def setUp(self):
        self.user = criar_voluntario('maria', '52998224725')
        self.outro = criar_voluntario('joao', '11144477735')
        inicio = timezone.now() + timedelta(days=2)
        self.alheia = Ocupado.objects.create(
            usuario=self.outro, data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        self.client.force_login(self.user)

    def test_nao_ve_nem_exclui_indisponibilidade_de_outro(self):
        # 404, que o handler404 do site transforma em redirecionamento para a home.
        resp = self.client.get(reverse('detalhes_ocupado', args=[self.alheia.pk]))
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        resp = self.client.post(reverse('excluir_ocupado', args=[self.alheia.pk]))
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        self.assertTrue(Ocupado.objects.filter(pk=self.alheia.pk).exists())

    def test_exclui_a_propria(self):
        inicio = timezone.now() + timedelta(days=3)
        minha = Ocupado.objects.create(usuario=self.user, data_inicio=inicio, data_fim=inicio + timedelta(hours=1))
        self.client.post(reverse('excluir_ocupado', args=[minha.pk]))
        self.assertFalse(Ocupado.objects.filter(pk=minha.pk).exists())

    def test_por_evento_exige_login_e_respeita_visibilidade(self):
        inicio = timezone.now() + timedelta(days=5)
        publico = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        privado = Evento.objects.create(
            nome='Ensaio fechado', data_inicio=inicio, data_fim=inicio + timedelta(hours=2),
            equipe=Equipe.objects.create(nome='Louvor'))

        resp = self.client.get(reverse('registrar_por_evento'))
        self.assertContains(resp, 'Culto')
        self.assertNotContains(resp, 'Ensaio fechado')

        self.client.post(
            reverse('processar_indisponibilidade_evento'), {'event_ids': [publico.pk, privado.pk]})
        self.assertTrue(Ocupado.objects.filter(usuario=self.user, evento=publico).exists())
        self.assertFalse(Ocupado.objects.filter(usuario=self.user, evento=privado).exists())

        self.client.logout()
        resp = self.client.get(reverse('registrar_por_evento'))
        self.assertEqual(resp.status_code, 302)
