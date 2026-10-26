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
        self.assertEqual(resp.context['aparelhos_ativos'], 1)
        self.assertEqual(resp.context['aparelhos_total'], 2)
        self.assertContains(resp, 'Moto G')
        self.assertContains(resp, 'Maria')

        resp = self.client.get(reverse('monitoramento_app'), {'aba': 'sessoes'})
        (sessao,) = resp.context['page_obj']
        self.assertEqual((sessao['usuario'], sessao['qtd']), (self.maria, 2))

    def test_filtros_de_aparelhos(self):
        self.client.force_login(self.admin)
        url = reverse('monitoramento_app')
        nomes = lambda resp: [a.usuario.username for a in resp.context['page_obj']]
        self.assertEqual(nomes(self.client.get(url, {'plataforma': 'ios'})), ['joao'])
        self.assertEqual(nomes(self.client.get(url, {'push': 'ativo'})), ['maria'])
        self.assertEqual(nomes(self.client.get(url, {'q': 'mar'})), ['maria'])
        self.assertEqual(self.client.get(url, {'aba': 'sessoes', 'q': 'joao'}).context['total_filtrado'], 0)

    def test_paginacao_de_aparelhos(self):
        for i in range(20):
            Device.objects.create(usuario=self.maria, expo_token=f'ExponentPushToken[x{i}]', plataforma='android')
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('monitoramento_app'))
        self.assertEqual(len(resp.context['page_obj']), 15)
        self.assertContains(resp, 'Página 1 de 2')
        self.assertEqual(len(self.client.get(reverse('monitoramento_app'), {'page': 2}).context['page_obj']), 7)


    def test_menu_mostra_link_so_para_superusuario(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/'), reverse('monitoramento_app'))
        self.client.force_login(self.joao)
        self.assertNotContains(self.client.get('/'), reverse('monitoramento_app'))


class MonitoramentoUsoTests(TestCase):
    def setUp(self):
        from usuario.models import RegistroLogin
        self.admin = criar('admin', '52998224725', is_superuser=True, is_staff=True)
        self.maria = criar('maria', '11144477735', first_name='Maria')
        for _ in range(17):
            RegistroLogin.objects.create(usuario=self.maria)
        antigo = RegistroLogin.objects.create(usuario=self.admin)
        RegistroLogin.objects.filter(pk=antigo.pk).update(data_hora=timezone.now() - timedelta(days=20))

    def test_acessos_filtrados_e_paginados(self):
        self.client.force_login(self.admin)  # este login também entra no registro (hoje)
        url = reverse('monitoramento_uso')
        resp = self.client.get(url)  # padrão: últimos 7 dias
        self.assertEqual(resp.context['page_obj'].paginator.count, 18)
        self.assertEqual(len(resp.context['page_obj']), 15)
        self.assertContains(resp, 'Página 1 de 2')
        self.assertEqual(self.client.get(url, {'periodo': '30'}).context['page_obj'].paginator.count, 19)
        resp = self.client.get(url, {'periodo': 'todos', 'q': 'admin'})
        self.assertEqual((resp.context['page_obj'].paginator.count, resp.context['acessos_pessoas']), (2, 1))

    def test_so_superusuario(self):
        self.client.force_login(self.maria)
        self.assertEqual(self.client.get(reverse('monitoramento_uso')).status_code, 403)
