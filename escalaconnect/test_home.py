from django.test import TestCase
from django.utils import timezone


class FaixaBaixeOAppTests(TestCase):
    """Faixa "Baixe o app" no Início: só para quem ainda não entrou pelo app, com a loja do aparelho."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(
            username='maria', password='x', cpf='52998224725', email='maria@example.com',
            is_first_login=False, termo_aceito_em=timezone.now())
        self.client.force_login(self.user)

    def inicio(self, agente=''):
        return self.client.get('/', HTTP_USER_AGENT=agente)

    def test_loja_conforme_o_aparelho(self):
        android = self.inicio('Mozilla/5.0 (Linux; Android 14; Pixel 8)')
        self.assertContains(android, 'Baixe o app')
        self.assertContains(android, 'play.google.com')
        self.assertNotContains(android, 'apps.apple.com')
        iphone = self.inicio('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)')
        self.assertContains(iphone, 'apps.apple.com')
        self.assertNotContains(iphone, 'play.google.com')
        computador = self.inicio('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        self.assertContains(computador, 'play.google.com')
        self.assertContains(computador, 'apps.apple.com')

    def test_quem_ja_usa_o_app_nao_ve(self):
        from knox.models import AuthToken
        AuthToken.objects.create(user=self.user)
        self.assertNotContains(self.inicio(), 'Baixe o app')
