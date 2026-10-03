from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from knox.models import AuthToken

from api.models import Device

User = get_user_model()


def criar(username, cpf, **extra):
    return User.objects.create_user(
        username=username, password='x', cpf=cpf, email=f'{username}@example.com',
        is_first_login=False, termo_aceito_em=timezone.now(), **extra)


class MonitoramentoAppTests(TestCase):
    def setUp(self):
        self.admin = criar('admin', '52998224725', is_superuser=True, is_staff=True)
        self.maria = criar('maria', '11144477735', first_name='Maria')
        self.joao = criar('joao', '39053344705')
        AuthToken.objects.create(user=self.maria)
        AuthToken.objects.create(user=self.maria)
        expirado, _ = AuthToken.objects.create(user=self.joao)
        AuthToken.objects.filter(pk=expirado.pk).update(expiry=timezone.now() - timedelta(days=1))
        Device.objects.create(usuario=self.maria, expo_token='ExponentPushToken[a]', plataforma='android', nome_aparelho='Moto G')
        Device.objects.create(usuario=self.joao, expo_token='ExponentPushToken[b]', plataforma='ios', ativo=False)

    def test_so_superusuario(self):
        url = reverse('monitoramento_app')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.joao)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_lista_aparelhos_e_sessoes_validas(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('monitoramento_app'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['usuarios_com_app'], 1)  # a sessão do João expirou
        self.assertEqual(resp.context['sessoes'][0]['qtd'], 2)
        self.assertEqual(resp.context['aparelhos_ativos'], 1)
        self.assertEqual(resp.context['aparelhos_total'], 2)
        self.assertContains(resp, 'Moto G')
        self.assertContains(resp, 'Maria')

    def test_menu_mostra_link_so_para_superusuario(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/'), reverse('monitoramento_app'))
        self.client.force_login(self.joao)
        self.assertNotContains(self.client.get('/'), reverse('monitoramento_app'))
