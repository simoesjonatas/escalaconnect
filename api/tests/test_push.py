"""Push: registro de aparelho, envio pela Expo, disparos e link assinado de confirmação."""
from datetime import timedelta
from unittest import mock

import requests
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from api.models import Device
from api.tasks import enviar_push_task
from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala import services
from escala.models import Desistencia, Escala, Funcao
from escalaconnect.confirmacao import token_de_confirmacao
from escalaconnect.notificacoes import pedir_confirmacao
from evento.models import Evento, Notification

from .test_conta import ApiTestCase, criar_usuario

TOKEN = 'ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]'
OUTRO_TOKEN = 'ExponentPushToken[bbbbbbbbbbbbbbbbbbbbbb]'


def resposta_da_expo(dados):
    resposta = mock.Mock()
    resposta.json.return_value = {'data': dados}
    return resposta


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)  # tasks rodam na hora, sem broker
class PushTestCase(ApiTestCase):
    """Base: voluntário com aparelho registrado e uma escala futura. A Expo é sempre simulada."""

    def setUp(self):
        super().setUp()
        self.user = criar_usuario()
        self.equipe = Equipe.objects.create(nome='Recepção')
        self.funcao = Funcao.objects.create(nome='Porta', equipe=self.equipe)
        inicio = timezone.now() + timedelta(days=3)
        self.evento = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        self.escala = Escala.objects.create(usuario=self.user, funcao=self.funcao, evento=self.evento)
        self.device = Device.objects.create(usuario=self.user, expo_token=TOKEN, plataforma='android')

        # O que a Expo simulada responde: um ticket por mensagem enviada e os recibos de entrega.
        self.tickets = [{'status': 'ok', 'id': 't1'}]
        self.recibos = {}
        patcher = mock.patch('api.push.requests.post', side_effect=self.responder)
        self.post = patcher.start()
        self.addCleanup(patcher.stop)

    def responder(self, url, **kwargs):
        return resposta_da_expo(self.tickets if url.endswith('/send') else self.recibos)

    def mensagens(self):
        """Mensagens enviadas à Expo (ignora as consultas de recibo)."""
        return [
            msg
            for chamada in self.post.call_args_list if chamada.args[0].endswith('/send')
            for msg in chamada.kwargs['json']
        ]


class DeviceTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = criar_usuario()
        self.autenticar(self.user)

    def registrar(self, token=TOKEN, **extra):
        return self.client.post('/api/v1/devices/', {'expo_token': token, 'plataforma': 'android', **extra}, format='json')

    def test_registra_e_atualiza_sem_duplicar(self):
        self.assertEqual(self.registrar(nome_aparelho='Moto G').status_code, 204)
        self.assertEqual(self.registrar(nome_aparelho='Moto G', app_versao='1.0.1').status_code, 204)
        device = Device.objects.get()
        self.assertEqual((device.usuario, device.app_versao, device.ativo), (self.user, '1.0.1', True))

    def test_token_invalido(self):
        resp = self.registrar(token='qualquer-coisa')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('expo_token', resp.data['errors'])

    def test_aparelho_passa_para_quem_entrou_por_ultimo(self):
        self.registrar()
        outro = criar_usuario(username='joao', cpf='11144477735')
        self.autenticar(outro)
        self.registrar()
        self.assertEqual(Device.objects.get().usuario, outro)

    def test_remover_desativa_so_o_proprio_aparelho(self):
        self.registrar()
        outro = criar_usuario(username='joao', cpf='11144477735')
        Device.objects.create(usuario=outro, expo_token=OUTRO_TOKEN, plataforma='ios')
        self.assertEqual(self.client.delete(f'/api/v1/devices/{OUTRO_TOKEN}/').status_code, 204)
        self.assertTrue(Device.objects.get(expo_token=OUTRO_TOKEN).ativo)
        self.assertEqual(self.client.delete(f'/api/v1/devices/{TOKEN}/').status_code, 204)
        self.assertFalse(Device.objects.get(expo_token=TOKEN).ativo)

    def test_registro_liberado_com_conta_pendente_e_logout_all_desativa(self):
        self.autenticar(criar_usuario(username='novo', cpf='39053344705', liberado=False))
        self.assertEqual(self.registrar(token=OUTRO_TOKEN).status_code, 204)
        self.client.post('/api/v1/auth/logout-all/')
        self.assertFalse(Device.objects.get(expo_token=OUTRO_TOKEN).ativo)


class EnvioTests(PushTestCase):
    def enviar(self, **extra):
        return enviar_push_task(
            self.user.pk, 'Título', 'Corpo', 'escalado', Notification.PURPOSE_ASSIGNED,
            escala_id=self.escala.pk, **extra)

    def test_envia_para_os_aparelhos_ativos_e_registra(self):
        Device.objects.create(usuario=self.user, expo_token=OUTRO_TOKEN, plataforma='ios', ativo=False)
        self.assertEqual(self.enviar(), 'sent')
        (msg,) = self.mensagens()
        self.assertEqual(msg['to'], TOKEN)
        self.assertEqual(msg['data'], {'tipo': 'escalado', 'escala_id': self.escala.pk})
        notif = Notification.objects.get(channel=Notification.CHANNEL_PUSH)
        self.assertEqual((notif.usuario, notif.escala, notif.last_status, notif.success_count),
                         (self.user, self.escala, 'sent', 1))
        self.assertEqual(notif.attempts.get().response_metadata['tickets'][0]['id'], 't1')

    def test_sem_aparelho_nao_chama_a_expo(self):
        self.device.delete()
        self.assertEqual(self.enviar(), 'sem_aparelho')
        self.post.assert_not_called()
        self.assertFalse(Notification.objects.exists())

    def test_token_morto_no_ticket_desativa_o_aparelho(self):
        self.tickets = [{'status': 'error', 'message': '...', 'details': {'error': 'DeviceNotRegistered'}}]
        self.assertEqual(self.enviar(), 'error')
        self.device.refresh_from_db()
        self.assertFalse(self.device.ativo)

    def test_token_morto_no_recibo_desativa_o_aparelho(self):
        self.recibos = {'t1': {'status': 'error', 'details': {'error': 'DeviceNotRegistered'}}}
        self.enviar()  # nos testes a conferência de recibos roda em seguida
        self.device.refresh_from_db()
        self.assertFalse(self.device.ativo)

    def test_throttle(self):
        self.assertEqual(self.enviar(throttle_horas=6), 'sent')
        self.assertEqual(self.enviar(throttle_horas=6), 'throttled')
        self.assertEqual(len(self.mensagens()), 1)

    def test_falha_de_rede_registra_erro_e_propaga_para_o_celery_tentar_de_novo(self):
        self.post.side_effect = requests.ConnectionError('fora do ar')
        with self.assertRaises(requests.ConnectionError):
            self.enviar()
        self.assertEqual(Notification.objects.get().last_status, 'error')


class DisparosTests(PushTestCase):
    """Cada ponto do sistema que deve avisar o voluntário no app."""

    def titulos(self):
        return [m['title'] for m in self.mensagens()]

    def test_ser_escalado_avisa_uma_vez(self):
        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)  # vaga em aberto: sem aviso
        with self.captureOnCommitCallbacks(execute=True):
            vaga.usuario = self.user
            vaga.save()
        with self.captureOnCommitCallbacks(execute=True):
            vaga.confirmada = True
            vaga.save()  # salvar de novo sem trocar o usuário não repete o aviso
        (msg,) = self.mensagens()
        self.assertEqual(msg['title'], 'Você foi escalado')
        self.assertIn('Culto', msg['body'])
        self.assertEqual(msg['data']['escala_id'], vaga.pk)

    def test_escala_em_evento_passado_nao_avisa(self):
        inicio = timezone.now() - timedelta(days=3)
        passado = Evento.objects.create(nome='Antigo', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        with self.captureOnCommitCallbacks(execute=True):
            Escala.objects.create(usuario=self.user, funcao=self.funcao, evento=passado)
        self.assertEqual(self.mensagens(), [])

    def test_quem_nao_tem_o_app_nao_gera_envio(self):
        sem_app = criar_usuario(username='joao', cpf='11144477735')
        with self.captureOnCommitCallbacks(execute=True):
            Escala.objects.create(usuario=sem_app, funcao=self.funcao, evento=self.evento)
        self.post.assert_not_called()

    def test_pedido_de_confirmacao_manda_email_e_push(self):
        sem_email = criar_usuario(username='joao', cpf='11144477735', email='')
        Device.objects.create(usuario=sem_email, expo_token=OUTRO_TOKEN, plataforma='android')
        Escala.objects.create(usuario=sem_email, funcao=self.funcao, evento=self.evento)
        Escala.objects.create(funcao=self.funcao, evento=self.evento)  # vaga em aberto é ignorada
        with self.captureOnCommitCallbacks(execute=True):
            emails = pedir_confirmacao(self.evento)
        self.assertEqual(emails, 1)  # só quem tem e-mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.titulos(), ['Confirme sua presença', 'Confirme sua presença'])  # push para os dois

    def test_aprovar_desistencia_e_troca_avisam_o_voluntario(self):
        desistencia = Desistencia.objects.create(escala=self.escala, usuario=self.user, motivo='Viagem')
        with self.captureOnCommitCallbacks(execute=True):
            services.aprovar_desistencia(desistencia)
        self.assertEqual(self.titulos(), ['Impedimento aceito'])

        outra = Escala.objects.create(usuario=self.user, funcao=self.funcao, evento=self.evento)
        self.post.reset_mock()
        troca = services.solicitar_troca(outra, self.user)
        with self.captureOnCommitCallbacks(execute=True):
            services.aprovar_troca(troca, criar_usuario(username='lider', cpf='39053344705'))
        self.assertEqual(self.titulos(), ['Troca aprovada'])

    def test_entrada_na_equipe_aprovada_avisa(self):
        lider = criar_usuario(username='lider', cpf='39053344705')
        Lideranca.objects.create(usuario=lider, equipe=self.equipe)
        membro = MembrosEquipe.objects.create(usuario=self.user, equipe=self.equipe)
        self.client.force_login(lider)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.get(reverse('aprovar_membro', args=[self.equipe.pk, membro.pk]))
        self.assertEqual(self.titulos(), ['Você entrou na equipe'])


class NotificarPeloSiteTests(PushTestCase):
    """As rotas que disparam e-mails agora exigem quem pode gerenciar o evento."""

    def test_anonimo_e_voluntario_comum_nao_disparam(self):
        for nome in ('evento_notificar_confirmacao', 'evento_notificar_colaboradores', 'evento_notificar_confirmacao_2'):
            url = reverse(nome, args=[self.evento.pk])
            self.assertEqual(self.client.get(url).status_code, 302)  # anônimo vai para o login
            self.client.force_login(self.user)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.client.logout()
        self.assertEqual(mail.outbox, [])

    def test_admin_dispara(self):
        self.client.force_login(criar_usuario(username='admin', cpf='11144477735', is_staff=True))
        self.client.get(reverse('evento_notificar_confirmacao', args=[self.evento.pk]))
        self.assertEqual(len(mail.outbox), 1)


class LinkDeConfirmacaoTests(TestCase):
    def setUp(self):
        self.user = criar_usuario()
        self.outro = criar_usuario(username='joao', cpf='11144477735')
        funcao = Funcao.objects.create(nome='Porta', equipe=Equipe.objects.create(nome='Recepção'))
        inicio = timezone.now() + timedelta(days=3)
        evento = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        self.escala = Escala.objects.create(usuario=self.user, funcao=funcao, evento=evento)
        self.outra = Escala.objects.create(usuario=self.outro, funcao=funcao, evento=evento)
        self.url = reverse('minhas_escalas_confirmar', args=[evento.pk, self.escala.pk])
        self.url_da_outra = reverse('minhas_escalas_confirmar', args=[evento.pk, self.outra.pk])

    def confirmada(self, escala):
        escala.refresh_from_db()
        return escala.confirmada

    def test_link_sem_token_nao_confirma_mais(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])
        self.assertFalse(self.confirmada(self.escala))

    def test_link_assinado_confirma_sem_login(self):
        self.client.get(f'{self.url}?t={token_de_confirmacao(self.escala)}')
        self.assertTrue(self.confirmada(self.escala))

    def test_token_de_uma_escala_nao_confirma_outra(self):
        self.client.get(f'{self.url_da_outra}?t={token_de_confirmacao(self.escala)}')
        self.assertFalse(self.confirmada(self.outra))

    def test_token_adulterado(self):
        self.client.get(f'{self.url}?t={token_de_confirmacao(self.escala)}x')
        self.assertFalse(self.confirmada(self.escala))

    def test_token_deixa_de_valer_se_a_escala_mudou_de_pessoa(self):
        token = token_de_confirmacao(self.escala)
        self.escala.usuario = self.outro
        self.escala.save()
        self.client.get(f'{self.url}?t={token}')
        self.assertFalse(self.confirmada(self.escala))

    def test_dono_logado_confirma_mesmo_sem_token_e_outro_usuario_nao(self):
        self.client.force_login(self.outro)
        self.client.get(self.url)
        self.assertFalse(self.confirmada(self.escala))
        self.client.force_login(self.user)
        self.client.get(self.url)
        self.assertTrue(self.confirmada(self.escala))

    def test_email_leva_o_link_assinado(self):
        from escalaconnect.tasks import enviar_email_confirmacao_task
        enviar_email_confirmacao_task(self.escala.pk)
        corpo = mail.outbox[0].body
        self.assertIn(f'?t={token_de_confirmacao(self.escala)}'[:20], corpo)
        link = corpo[corpo.index('http'):].split()[0]
        self.client.get(link[link.index('/api/'):])
        self.assertTrue(self.confirmada(self.escala))
