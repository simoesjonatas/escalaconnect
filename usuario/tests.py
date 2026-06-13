from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from usuario.utils import normalizar_telefone, validate_telefone, formatar_telefone
from usuario.forms import PerfilContatoForm
from usuario.forms_signup import SignupForm

User = get_user_model()


class TelefoneUtilsTests(TestCase):
    def test_normaliza_mascaras_e_espacos(self):
        self.assertEqual(normalizar_telefone('(21) 97267-7556'), '21972677556')
        self.assertEqual(normalizar_telefone('21 98851-6885'), '21988516885')
        self.assertEqual(normalizar_telefone('21 969008025'), '21969008025')

    def test_normaliza_codigo_do_brasil(self):
        self.assertEqual(normalizar_telefone('+5521992769489'), '21992769489')
        self.assertEqual(normalizar_telefone('5521992769489'), '21992769489')
        self.assertEqual(normalizar_telefone('+55 (21) 3333-4444'), '2133334444')

    def test_nao_inventa_ddd_para_numero_curto(self):
        # 9 dígitos sem DDD: só limpa a formatação, não adivinha o DDD.
        self.assertEqual(normalizar_telefone('96900-8025'), '969008025')

    def test_vazio_passa_direto(self):
        self.assertEqual(normalizar_telefone(''), '')
        self.assertIsNone(normalizar_telefone(None))

    def test_validate_aceita_10_e_11_digitos(self):
        validate_telefone('2133334444')      # fixo
        validate_telefone('21992769489')     # celular
        validate_telefone('')                # opcional

    def test_validate_rejeita_sem_ddd_ou_invalido(self):
        with self.assertRaises(ValidationError):
            validate_telefone('969008025')   # 9 dígitos, sem DDD
        with self.assertRaises(ValidationError):
            validate_telefone('0199276948')  # DDD começando com 0

    def test_formatar_para_exibicao(self):
        self.assertEqual(formatar_telefone('21992769489'), '(21) 99276-9489')
        self.assertEqual(formatar_telefone('2133334444'), '(21) 3333-4444')
        self.assertEqual(formatar_telefone(''), '')
        # Valor fora do padrão é exibido como está (não mente sobre o dado).
        self.assertEqual(formatar_telefone('969008025'), '969008025')


class SignupTelefoneTests(TestCase):
    def test_signup_normaliza_telefone(self):
        form = SignupForm(data={
            'first_name': 'Ana',
            'last_name': 'Silva',
            'email': 'ana@example.com',
            'password1': 'Senha-forte-123',
            'password2': 'Senha-forte-123',
            'telefone': '+55 (21) 99276-9489',
            'cpf': '52998224725',  # CPF válido (dígitos verificadores corretos)
            'aceitar_termos': True,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['telefone'], '21992769489')

    def test_signup_rejeita_telefone_sem_ddd(self):
        form = SignupForm(data={
            'first_name': 'Bia',
            'last_name': 'Souza',
            'email': 'bia@example.com',
            'password1': 'Senha-forte-123',
            'password2': 'Senha-forte-123',
            'telefone': '99276-9489',
            'cpf': '52998224725',
            'aceitar_termos': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('telefone', form.errors)


class SignupPageSmokeTests(TestCase):
    def test_pagina_de_cadastro_renderiza_com_mascara(self):
        resp = self.client.get(reverse('signup'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'telefone-mask.js')


class PerfilContatoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='vol_perfil', password='x', cpf='10000006001',
            email='antigo@example.com',
            is_first_login=False, termo_aceito_em=now(),
        )

    def test_atualiza_email_e_telefone_normalizado(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse('perfil_usuario'), {
            'email': 'novo@example.com',
            'telefone': '+55 (21) 99276-9489',
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'novo@example.com')
        self.assertEqual(self.user.telefone, '21992769489')

    def test_rejeita_telefone_sem_ddd(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse('perfil_usuario'), {
            'email': 'antigo@example.com',
            'telefone': '99276-9489',
        })
        self.assertEqual(resp.status_code, 200)  # re-renderiza com erro
        self.user.refresh_from_db()
        self.assertIsNone(self.user.telefone)

    def test_rejeita_email_de_outro_usuario(self):
        User.objects.create_user(
            username='outro', password='x', cpf='10000006002',
            email='ocupado@example.com',
        )
        self.client.force_login(self.user)
        resp = self.client.post(reverse('perfil_usuario'), {
            'email': 'ocupado@example.com',
            'telefone': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'antigo@example.com')

    def test_form_perfil_exibe_so_email_e_telefone(self):
        form = PerfilContatoForm(instance=self.user)
        self.assertEqual(list(form.fields.keys()), ['email', 'telefone'])


class HomeAvisoContatoTests(TestCase):
    def _user(self, username, cpf, **kwargs):
        return User.objects.create_user(
            username=username, password='x', cpf=cpf,
            is_first_login=False, termo_aceito_em=now(), **kwargs,
        )

    def test_aviso_quando_falta_telefone(self):
        user = self._user('sem_fone', '10000007001', email='a@example.com')
        self.client.force_login(user)
        resp = self.client.get('/')
        self.assertContains(resp, 'telefone válido')
        self.assertContains(resp, 'Atualizar contato')

    def test_aviso_quando_telefone_sem_ddd(self):
        user = self._user(
            'fone_sem_ddd', '10000007002',
            email='b@example.com', telefone='969008025',
        )
        self.client.force_login(user)
        resp = self.client.get('/')
        self.assertContains(resp, 'telefone válido')

    def test_sem_aviso_quando_contato_completo(self):
        user = self._user(
            'completo', '10000007003',
            email='c@example.com', telefone='21992769489',
        )
        self.client.force_login(user)
        resp = self.client.get('/')
        self.assertNotContains(resp, 'Atualizar contato')
