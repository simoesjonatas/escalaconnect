from django.test import TestCase, override_settings


class PrivacidadeTests(TestCase):
    def test_pagina_publica(self):
        resp = self.client.get('/privacidade/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Política de Privacidade')
        self.assertNotContains(resp, 'mailto:')

    @override_settings(PRIVACIDADE_CONTATO='contato@example.com')
    def test_mostra_contato_quando_configurado(self):
        self.assertContains(self.client.get('/privacidade/'), 'mailto:contato@example.com')
