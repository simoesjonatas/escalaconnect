from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.test import APITestCase

from usuario.models import AtividadeDiaria, RegistroLogin

User = get_user_model()


def criar_usuario(username='maria', cpf='52998224725', liberado=True, **extra):
    """Voluntário com senha definida e termo aceito (a menos que liberado=False)."""
    campos = {'email': f'{username}@example.com', 'cpf': cpf}
    if liberado:
        campos.update(is_first_login=False, termo_aceito_em=timezone.now())
    campos.update(extra)
    return User.objects.create_user(username=username, password='senha-forte-123', **campos)


class ApiTestCase(APITestCase):
    def setUp(self):
        cache.clear()  # throttle de login e de atividade ficam no cache

    def autenticar(self, user):
        _, token = AuthToken.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        return token


class LoginTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = criar_usuario()

    def login(self, username='maria', password='senha-forte-123'):
        return self.client.post('/api/v1/auth/login/', {'username': username, 'password': password}, format='json')

    def test_login_devolve_token_e_usuario_sem_cpf(self):
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['token'])
        self.assertEqual(resp.data['usuario']['username'], 'maria')
        self.assertFalse(resp.data['usuario']['precisa_definir_senha'])
        self.assertFalse(resp.data['usuario']['precisa_aceitar_termo'])
        self.assertNotIn('cpf', resp.data['usuario'])
        self.assertNotIn(self.user.cpf, resp.content.decode())

    def test_login_aceita_email(self):
        self.assertEqual(self.login(username='MARIA@example.com').status_code, 200)

    def test_login_registra_login_e_token_funciona(self):
        resp = self.login()
        self.assertEqual(RegistroLogin.objects.filter(usuario=self.user).count(), 1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {resp.data['token']}")
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 200)

    def test_senha_errada_devolve_400_com_codigo(self):
        resp = self.login(password='errada')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'credenciais_invalidas')
        self.assertFalse(AuthToken.objects.exists())

    def test_usuario_inativo_nao_entra(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 400)

    def test_campos_obrigatorios(self):
        resp = self.client.post('/api/v1/auth/login/', {}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'validacao')
        self.assertIn('username', resp.data['errors'])

    def test_email_duplicado_nao_gera_erro_500(self):
        criar_usuario(username='outra', cpf='11144477735', email='maria@example.com')
        self.assertEqual(self.login(username='maria@example.com').status_code, 400)
        self.assertEqual(self.login(username='maria').status_code, 200)

    def test_throttle_por_usuario(self):
        for _ in range(5):
            self.assertEqual(self.login(password='errada').status_code, 400)
        resp = self.login(password='errada')
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.data['code'], 'throttled')
        # A senha certa também fica bloqueada até a janela passar.
        self.assertEqual(self.login().status_code, 429)


class LogoutTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = criar_usuario()

    def test_logout_revoga_so_o_token_atual(self):
        AuthToken.objects.create(user=self.user)  # outro aparelho
        self.autenticar(self.user)
        self.assertEqual(self.client.post('/api/v1/auth/logout/').status_code, 204)
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)
        self.assertEqual(AuthToken.objects.filter(user=self.user).count(), 1)

    def test_logout_all_revoga_todos(self):
        AuthToken.objects.create(user=self.user)
        self.autenticar(self.user)
        self.assertEqual(self.client.post('/api/v1/auth/logout-all/').status_code, 204)
        self.assertFalse(AuthToken.objects.filter(user=self.user).exists())


class ContaLiberadaTests(ApiTestCase):
    def test_sem_token_devolve_401(self):
        resp = self.client.get('/api/v1/me/')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data['code'], 'not_authenticated')

    def test_token_invalido_devolve_401(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token invalido')
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)

    def test_senha_pendente(self):
        self.autenticar(criar_usuario(liberado=False))
        resp = self.client.get('/api/v1/me/')  # GET liberado para o app saber a pendência
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['precisa_definir_senha'])
        resp = self.client.patch('/api/v1/me/', {'telefone': '21992769489'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data['code'], 'senha_pendente')

    def test_termo_pendente(self):
        self.autenticar(criar_usuario(liberado=False, is_first_login=False))
        resp = self.client.patch('/api/v1/me/', {'telefone': '21992769489'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data['code'], 'termo_pendente')

    def test_staff_e_isento_do_termo(self):
        self.autenticar(criar_usuario(liberado=False, is_first_login=False, is_staff=True))
        resp = self.client.patch('/api/v1/me/', {'telefone': '21992769489'}, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_logout_liberado_com_pendencia(self):
        self.autenticar(criar_usuario(liberado=False))
        self.assertEqual(self.client.post('/api/v1/auth/logout/').status_code, 204)


class MeTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = criar_usuario()
        self.autenticar(self.user)

    def test_uso_da_api_conta_como_atividade(self):
        self.client.get('/api/v1/me/')
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.ultima_atividade)
        self.assertTrue(AtividadeDiaria.objects.filter(usuario=self.user).exists())

    def test_patch_atualiza_contato_e_normaliza_telefone(self):
        resp = self.client.patch('/api/v1/me/', {'telefone': '(21) 99276-9489'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telefone, '21992769489')
        self.assertEqual(self.user.email, 'maria@example.com')  # campo omitido não muda

    def test_patch_recusa_email_em_uso(self):
        criar_usuario(username='outra', cpf='11144477735')
        resp = self.client.patch('/api/v1/me/', {'email': 'outra@example.com'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'validacao')
        self.assertIn('email', resp.data['errors'])

    def test_patch_nao_altera_outros_campos(self):
        self.client.patch('/api/v1/me/', {'username': 'hacker', 'is_staff': True}, format='json')
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'maria')
        self.assertFalse(self.user.is_staff)


class RotasTests(ApiTestCase):
    def test_meta_e_publica(self):
        resp = self.client.get('/api/v1/meta/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('min_build', resp.data)

    def test_rota_inexistente_devolve_404_json(self):
        resp = self.client.get('/api/v1/nao-existe/')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()['code'], 'not_found')

    def test_site_continua_respondendo_html(self):
        resp = self.client.get('/login/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/html', resp['Content-Type'])
