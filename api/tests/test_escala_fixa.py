"""Escala fixa pelo app do líder e pela página do site (regras testadas em escala/test_fixa.py)."""
from django.test import override_settings
from django.urls import reverse

from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala.models import Escala, EscalaFixa, EscalaFixaItem, Funcao
from escala.test_fixa import DOMINGO, MANHA, EscalaFixaTestCase

from .test_conta import ApiTestCase, criar_usuario


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class EscalaFixaApiTests(ApiTestCase, EscalaFixaTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        EscalaFixaTestCase.setUp(self)
        self.fixa.ativa = False
        self.fixa.save()
        self.lider = criar_usuario('lider', cpf='39053344705')
        Lideranca.objects.create(equipe=self.equipe, usuario=self.lider)
        self.autenticar(self.lider)
        self.url = f'/api/v1/lider/equipes/{self.equipe.pk}/escala-fixa/'

    def linha(self, **mudancas):
        dados = {'dia_semana': DOMINGO, 'turno': MANHA, 'semana': 0, 'funcao_id': self.mesa.pk,
                 'usuario_id': self.ana.pk, **mudancas}
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url + 'itens/', dados, format='json')

    def test_monta_liga_edita_e_exclui(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['ativa'])
        self.assertEqual([f['nome'] for f in resp.data['funcoes']], ['Mesa', 'Palco'])
        self.assertEqual(len(resp.data['membros']), 3)

        resp = self.linha()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['item']['quando'], 'Todo domingo')
        self.assertEqual(resp.data['item']['culto'], 'Domingo de manhã')
        self.assertEqual(resp.data['preenchidas'], 0)  # desligada: só guarda a linha
        self.assertEqual(resp.data['resumo'], 'Linha salva. Ligue a escala fixa para preencher os cultos.')

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.patch(self.url, {'ativa': True}, format='json')
        self.assertEqual(resp.data['preenchidas'], len(self.manhas))
        self.assertIn('cultos preenchidos', resp.data['resumo'])

        item = EscalaFixaItem.objects.get()
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.patch(f'/api/v1/lider/escala-fixa/itens/{item.pk}/',
                                     {'dia_semana': DOMINGO, 'turno': MANHA, 'semana': 0,
                                      'funcao_id': self.mesa.pk, 'usuario_id': self.bia.pk}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['item']['usuario']['id'], self.bia.pk)
        self.assertEqual(self.quem(self.manhas[0]), ['bia'])

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.delete(f'/api/v1/lider/escala-fixa/itens/{item.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.quem(self.manhas[0]), [None])

    def test_erros_de_validacao(self):
        outra = Funcao.objects.create(nome='Porta', equipe=Equipe.objects.create(nome='Recepção'))
        self.assertEqual(self.linha(funcao_id=outra.pk).status_code, 404)
        resp = self.linha(usuario_id=self.lider.pk)
        self.assertEqual((resp.status_code, resp.data['code']), (400, 'nao_membro'))
        resp = self.linha(turno='madrugada')
        self.assertEqual((resp.status_code, resp.data['code']), (400, 'turno_invalido'))

    def test_so_o_lider_da_equipe(self):
        outra = Equipe.objects.create(nome='Louvor')
        outro_lider = criar_usuario('outro', cpf='71428793860')
        Lideranca.objects.create(equipe=outra, usuario=outro_lider)
        item = EscalaFixaItem.objects.create(escala_fixa=self.fixa, dia_semana=DOMINGO, turno=MANHA,
                                             funcao=self.mesa, usuario=self.ana)
        self.autenticar(outro_lider)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.delete(f'/api/v1/lider/escala-fixa/itens/{item.pk}/').status_code, 404)
        self.autenticar(self.ana)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertTrue(EscalaFixaItem.objects.exists())


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class EscalaFixaNoSiteTests(EscalaFixaTestCase):
    def setUp(self):
        super().setUp()
        self.lider = criar_usuario('lider', cpf='39053344705')
        Lideranca.objects.create(equipe=self.equipe, usuario=self.lider)
        self.client.force_login(self.lider)
        self.url = reverse('escala_fixa_equipe', args=[self.equipe.pk])

    def test_pagina_adiciona_e_preenche(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(self.url, {'acao': 'adicionar', 'dia_semana': DOMINGO, 'turno': MANHA,
                                               'semana': 3, 'funcao': self.mesa.pk, 'usuario': self.bia.pk},
                                    follow=True)
        self.assertContains(resp, '3º domingo do mês')
        self.assertContains(resp, '1 culto preenchido')
        self.assertEqual(self.quem(self.manhas[2]), ['bia'])

    def test_voluntario_nao_entra(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url).status_code, 403)
