from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from api.models import Aviso, Device
from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala.models import Escala, Funcao
from evento.models import Evento

from .test_conta import ApiTestCase, criar_usuario

User = get_user_model()


def cpf_valido(base):
    """Completa 9 dígitos com os dois dígitos verificadores."""
    digitos = [int(c) for c in base]
    for tamanho in (9, 10):
        soma = sum(d * (tamanho + 1 - i) for i, d in enumerate(digitos[:tamanho]))
        resto = soma * 10 % 11
        digitos.append(0 if resto == 10 else resto)
    return ''.join(map(str, digitos))


DADOS = {
    'first_name': 'Ana',
    'last_name': 'Souza',
    'email': 'ana@example.com',
    'cpf': cpf_valido('123456789'),
    'telefone': '(21) 99999-1234',
    'aniversario': '1995-04-10',
    'password1': 'uma-senha-boa-42',
    'password2': 'uma-senha-boa-42',
}


class CadastroTests(ApiTestCase):
    def cadastrar(self, **mudancas):
        return self.client.post('/api/v1/auth/cadastro/', {**DADOS, **mudancas}, format='json')

    def test_cria_a_conta_e_ja_entra_com_o_termo_pendente(self):
        resp = self.cadastrar()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('token', resp.data)
        usuario = resp.data['usuario']
        self.assertEqual(usuario['username'], 'ana.souza')
        self.assertFalse(usuario['precisa_definir_senha'])
        self.assertTrue(usuario['precisa_aceitar_termo'])
        self.assertFalse(usuario['em_equipe'])
        self.assertNotIn('cpf', usuario)

        criado = User.objects.get(username='ana.souza')
        self.assertTrue(criado.check_password('uma-senha-boa-42'))
        self.assertEqual(criado.telefone, '21999991234')

        # O token devolvido já vale para aceitar o termo e seguir.
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {resp.data['token']}")
        self.assertEqual(self.client.post('/api/v1/me/aceitar-termo/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/equipes/').status_code, 200)

    def test_homonimo_ganha_numero_no_usuario(self):
        criar_usuario(username='ana.souza')
        resp = self.cadastrar()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['usuario']['username'], 'ana.souza2')

    def test_cpf_ou_email_ja_cadastrados(self):
        criar_usuario(username='outra', cpf=DADOS['cpf'], email='outra@example.com')
        resp = self.cadastrar()
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Esqueci minha senha', resp.data['errors']['cpf'][0])

        resp = self.cadastrar(cpf=cpf_valido('987654321'), email='OUTRA@example.com')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('email', resp.data['errors'])

    def test_validacoes(self):
        resp = self.cadastrar(cpf='12345678900', password2='outra-senha-99', aniversario='')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(set(resp.data['errors']), {'cpf', 'password2', 'aniversario'})
        self.assertFalse(User.objects.filter(first_name='Ana').exists())


class ExcluirContaTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = criar_usuario(first_name='Maria', last_name='Lima', telefone='21988887777')
        self.lider = criar_usuario(username='lider', cpf=cpf_valido('111222333'))
        self.equipe = Equipe.objects.create(nome='Recepção')
        Lideranca.objects.create(equipe=self.equipe, usuario=self.lider)
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=self.user, aprovado=True)
        self.funcao = Funcao.objects.create(nome='Porta', equipe=self.equipe)
        self.passada = self.escala(dias=-7)
        self.futura = self.escala(dias=5, confirmada=True)
        Device.objects.create(usuario=self.user, expo_token='ExponentPushToken[maria]')
        self.autenticar(self.user)

    def escala(self, dias, **extra):
        inicio = timezone.now() + timedelta(days=dias)
        evento = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        return Escala.objects.create(evento=evento, funcao=self.funcao, usuario=self.user, **extra)

    def excluir(self, senha='senha-forte-123'):
        return self.client.post('/api/v1/me/excluir-conta/', {'senha': senha}, format='json')

    def test_senha_errada_nao_exclui(self):
        resp = self.excluir('errada')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'senha_incorreta')
        self.assertTrue(User.objects.get(pk=self.user.pk).is_active)

    def test_anonimiza_libera_as_escalas_futuras_e_avisa_o_lider(self):
        self.assertEqual(self.excluir().status_code, 204)

        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.get_full_name(), 'Ex-voluntário')
        self.assertEqual((user.email, user.telefone, user.aniversario), ('', None, None))
        self.assertNotEqual(user.cpf, '52998224725')
        self.assertFalse(user.auth_token_set.exists())
        self.assertFalse(Device.objects.filter(usuario=user).exists())
        self.assertFalse(MembrosEquipe.objects.filter(usuario=user).exists())

        # O histórico continua contando; a escala futura virou vaga.
        self.passada.refresh_from_db()
        self.futura.refresh_from_db()
        self.assertEqual(self.passada.usuario_id, user.pk)
        self.assertIsNone(self.futura.usuario_id)
        self.assertFalse(self.futura.confirmada)

        aviso = Aviso.objects.get(usuario=self.lider)
        self.assertEqual(aviso.titulo, 'Vaga aberta na escala')
        self.assertIn('Maria Lima saiu do Connect', aviso.corpo)

        # A sessão antiga e o login deixam de valer.
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 401)
        self.client.credentials()
        resp = self.client.post('/api/v1/auth/login/', {'username': 'maria', 'password': 'senha-forte-123'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_mesmo_cpf_pode_criar_conta_nova_depois(self):
        self.excluir()
        self.client.credentials()
        resp = self.client.post('/api/v1/auth/cadastro/', {**DADOS, 'cpf': '52998224725'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_admin_nao_exclui_pelo_app(self):
        self.user.is_staff = True
        self.user.save()
        resp = self.excluir()
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'conta_admin')


class ExcluirContaNoSiteTests(ApiTestCase):
    def test_pagina_do_perfil_exclui_com_a_senha(self):
        user = criar_usuario()
        self.client.force_login(user)
        url = reverse('excluir_conta')
        self.assertEqual(self.client.get(url).status_code, 200)

        resp = self.client.post(url, {'senha': 'errada'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.get(pk=user.pk).is_active)

        resp = self.client.post(url, {'senha': 'senha-forte-123'})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(User.objects.get(pk=user.pk).is_active)
