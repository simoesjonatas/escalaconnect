from datetime import timedelta

from django.utils import timezone

from equipe.models import Equipe
from escala.models import Desistencia, Escala, Funcao, SolicitacaoTroca
from evento.models import Evento

from .test_conta import ApiTestCase, criar_usuario


class EscalasApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.equipe = Equipe.objects.create(nome='Recepção')
        self.funcao = Funcao.objects.create(nome='Porta', equipe=self.equipe)
        self.user = criar_usuario()
        self.outro = criar_usuario(username='joao', cpf='11144477735')
        self.escala = self.criar_escala(self.user, dias=3)
        self.escala_do_outro = self.criar_escala(self.outro, dias=3)
        self.autenticar(self.user)

    def criar_escala(self, usuario, dias, nome='Culto', **extra):
        inicio = timezone.now() + timedelta(days=dias)
        evento = Evento.objects.create(nome=nome, data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        return Escala.objects.create(usuario=usuario, funcao=self.funcao, evento=evento, **extra)

    def url(self, escala, sufixo=''):
        return f'/api/v1/escalas/{escala.pk}/{sufixo}'


class ListaEDetalheTests(EscalasApiTestCase):
    def test_lista_so_as_minhas_escalas_futuras_em_ordem(self):
        self.criar_escala(self.user, dias=-2, nome='Passado')
        depois = self.criar_escala(self.user, dias=10, nome='Depois')
        resp = self.client.get('/api/v1/escalas/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([e['id'] for e in resp.data], [self.escala.pk, depois.pk])

    def test_formato_da_escala(self):
        item = self.client.get(self.url(self.escala)).data
        self.assertEqual(item['evento']['nome'], 'Culto')
        self.assertEqual(item['funcao'], 'Porta')
        self.assertEqual(item['equipe'], 'Recepção')
        self.assertFalse(item['confirmada'])
        self.assertFalse(item['tem_impedimento'])
        self.assertFalse(item['troca_pendente'])

    def test_lista_nao_faz_consulta_por_escala(self):
        for dias in range(4, 9):
            self.criar_escala(self.user, dias=dias)
        self.client.get('/api/v1/escalas/')  # aquece o registro de atividade (1x por minuto)
        with self.assertNumQueries(3):  # 2 do token (knox) + 1 das escalas
            self.client.get('/api/v1/escalas/')

    def test_escala_de_outro_usuario_e_404_em_todas_as_rotas(self):
        alvo = self.escala_do_outro
        self.assertEqual(self.client.get(self.url(alvo)).status_code, 404)
        self.assertEqual(self.client.post(self.url(alvo, 'confirmar/')).status_code, 404)
        self.assertEqual(
            self.client.post(self.url(alvo, 'impedimento/'), {'motivo': 'x'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(self.url(alvo, 'troca/')).status_code, 404)
        self.assertEqual(self.client.delete(self.url(alvo, 'troca/')).status_code, 404)
        alvo.refresh_from_db()
        self.assertFalse(alvo.confirmada)
        self.assertFalse(Desistencia.objects.exists())
        self.assertFalse(SolicitacaoTroca.objects.exists())

    def test_exige_token(self):
        self.client.credentials()
        self.assertEqual(self.client.get('/api/v1/escalas/').status_code, 401)
        self.assertEqual(self.client.post(self.url(self.escala, 'confirmar/')).status_code, 401)

    def test_conta_pendente_nao_acessa_escalas(self):
        self.autenticar(criar_usuario(username='novo', cpf='39053344705', liberado=False))
        resp = self.client.get('/api/v1/escalas/')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data['code'], 'senha_pendente')


class ConfirmarTests(EscalasApiTestCase):
    def test_confirma(self):
        resp = self.client.post(self.url(self.escala, 'confirmar/'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['confirmada'])
        self.escala.refresh_from_db()
        self.assertTrue(self.escala.confirmada)
        self.assertIsNotNone(self.escala.data_confirmacao)

    def test_ja_confirmada(self):
        self.client.post(self.url(self.escala, 'confirmar/'))
        resp = self.client.post(self.url(self.escala, 'confirmar/'))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'ja_confirmada')

    def test_evento_encerrado(self):
        passada = self.criar_escala(self.user, dias=-2)
        resp = self.client.post(self.url(passada, 'confirmar/'))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'evento_encerrado')
        passada.refresh_from_db()
        self.assertFalse(passada.confirmada)


class ImpedimentoTests(EscalasApiTestCase):
    def sinalizar(self, escala, motivo='Viagem a trabalho'):
        return self.client.post(self.url(escala, 'impedimento/'), {'motivo': motivo}, format='json')

    def test_sinaliza_e_mantem_a_escala_ate_o_lider_aprovar(self):
        resp = self.sinalizar(self.escala)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['tem_impedimento'])
        desistencia = Desistencia.objects.get()
        self.assertEqual(desistencia.usuario, self.user)
        self.assertEqual(desistencia.motivo, 'Viagem a trabalho')
        self.escala.refresh_from_db()
        self.assertEqual(self.escala.usuario, self.user)

    def test_motivo_obrigatorio(self):
        resp = self.sinalizar(self.escala, motivo='')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'validacao')
        self.assertIn('motivo', resp.data['errors'])

    def test_nao_repete(self):
        self.sinalizar(self.escala)
        resp = self.sinalizar(self.escala)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'ja_sinalizado')
        self.assertEqual(Desistencia.objects.count(), 1)

    def test_evento_ja_iniciado(self):
        resp = self.sinalizar(self.criar_escala(self.user, dias=-1))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'evento_iniciado')


class TrocaTests(EscalasApiTestCase):
    def test_pede_e_cancela(self):
        resp = self.client.post(self.url(self.escala, 'troca/'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['troca_pendente'])
        troca = SolicitacaoTroca.objects.get()
        self.assertEqual((troca.solicitante, troca.escala_origem), (self.user, self.escala))

        resp = self.client.delete(self.url(self.escala, 'troca/'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['troca_pendente'])
        self.assertFalse(SolicitacaoTroca.objects.exists())

    def test_nao_repete_pedido(self):
        self.client.post(self.url(self.escala, 'troca/'))
        resp = self.client.post(self.url(self.escala, 'troca/'))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'solicitacao_pendente')

    def test_cancelar_sem_pedido(self):
        resp = self.client.delete(self.url(self.escala, 'troca/'))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'sem_solicitacao')


class HomeTests(EscalasApiTestCase):
    def test_pendencias_e_proxima_escala(self):
        self.criar_escala(self.user, dias=8, confirmada=True)
        resp = self.client.get('/api/v1/home/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['escalas_pendentes'], 1)
        self.assertTrue(resp.data['tem_escalas'])
        self.assertFalse(resp.data['tem_disponibilidade'])
        self.assertFalse(resp.data['falta_email'])
        self.assertTrue(resp.data['falta_telefone'])
        self.assertEqual(resp.data['proxima_escala']['id'], self.escala.pk)

    def test_sem_escalas(self):
        self.autenticar(criar_usuario(username='ana', cpf='39053344705'))
        resp = self.client.get('/api/v1/home/')
        self.assertEqual(resp.data['escalas_pendentes'], 0)
        self.assertIsNone(resp.data['proxima_escala'])
