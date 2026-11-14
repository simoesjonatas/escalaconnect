"""Monitor da fila do Celery: batimento, avisos por e-mail aos admins e /healthz/celery."""
import time
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from kombu.exceptions import OperationalError, VersionMismatch

from escalaconnect import monitor_fila
from escalaconnect.celery import app as celery_app, batimento

ADMIN = 'admin@example.com'


@override_settings(
    ADMINS=[(ADMIN, ADMIN)], MONITOR_FILA_BATIMENTO=True, MONITOR_FILA_MINUTOS=20,
    MONITOR_FILA_AVISO_HORAS=6, CELERY_TASK_ALWAYS_EAGER=True,
)
class MonitorTestCase(TestCase):
    def setUp(self):
        cache.clear()
        monitor_fila._travas_locais.clear()
        self.addCleanup(cache.clear)
        self.addCleanup(monitor_fila._travas_locais.clear)

    def bater(self, worker_min=None, beat_min=None, desde_min=60):
        """Simula o último batimento do worker/beat há N minutos (None = nunca)."""
        agora = time.time()
        cache.set(monitor_fila.CHAVE_DESDE, agora - desde_min * 60, None)
        for chave, minutos in ((monitor_fila.CHAVE_WORKER, worker_min), (monitor_fila.CHAVE_BEAT, beat_min)):
            if minutos is not None:
                cache.set(chave, agora - minutos * 60, None)

    def codigos(self, **kwargs):
        return [p.codigo for p in monitor_fila.verificar(**kwargs)]


class BatimentoTests(MonitorTestCase):
    def test_batimento_do_beat_marca_worker_e_beat(self):
        batimento.delay(origem='beat')
        self.assertIsNotNone(cache.get(monitor_fila.CHAVE_WORKER))
        self.assertIsNotNone(cache.get(monitor_fila.CHAVE_BEAT))

    def test_teste_do_monitor_marca_so_o_worker(self):
        batimento.delay(origem='monitor')
        self.assertIsNotNone(cache.get(monitor_fila.CHAVE_WORKER))
        self.assertIsNone(cache.get(monitor_fila.CHAVE_BEAT))

    def test_beat_agenda_o_batimento_e_o_worker_conhece_a_tarefa(self):
        agendada = celery_app.conf.beat_schedule['batimento']
        self.assertEqual(agendada['task'], 'escalaconnect.batimento')
        self.assertEqual(agendada['kwargs'], {'origem': 'beat'})
        self.assertIn('escalaconnect.batimento', celery_app.tasks)


class VerificarTests(MonitorTestCase):
    def test_batimentos_recentes_nao_sao_problema(self):
        self.bater(worker_min=3, beat_min=3)
        self.assertEqual(self.codigos(), [])

    def test_worker_sem_batimento_e_problema(self):
        self.bater(worker_min=45, beat_min=45)
        (problema,) = monitor_fila.verificar()
        self.assertEqual(problema.codigo, 'worker_parado')
        self.assertIn('45 min', problema.detalhe)

    def test_worker_de_pe_sem_batimento_do_beat_e_beat_parado(self):
        self.bater(worker_min=1, beat_min=30)  # o worker roda os testes do /healthz, mas nada do beat
        self.assertEqual(self.codigos(), ['beat_parado'])

    def test_nunca_visto_tem_carencia(self):
        self.bater(desde_min=5)  # deploy novo: o worker ainda não bateu
        self.assertEqual(self.codigos(), [])
        self.bater(desde_min=25)
        self.assertEqual(self.codigos(), ['worker_parado'])

    def test_primeira_olhada_comeca_a_carencia(self):
        self.assertEqual(self.codigos(), [])
        self.assertIsNotNone(cache.get(monitor_fila.CHAVE_DESDE))

    @override_settings(MONITOR_FILA_BATIMENTO=False)
    def test_sem_cache_compartilhado_nao_confere_batimento(self):
        self.bater(worker_min=600, beat_min=600)
        self.assertEqual(self.codigos(), [])

    def test_fila_que_recusa_publicacao(self):
        self.bater(worker_min=1, beat_min=1)
        with mock.patch.object(batimento, 'apply_async', side_effect=VersionMismatch('redis-py 5.3.1')):
            (problema,) = monitor_fila.verificar(publicar=True)
        self.assertEqual(problema.codigo, 'fila_indisponivel')
        self.assertIn('VersionMismatch', problema.detalhe)


class AvisarTests(MonitorTestCase):
    def test_um_email_por_problema_na_janela(self):
        worker = monitor_fila.Problema('worker_parado', 'parado há 45 min')
        self.assertEqual(monitor_fila.avisar([worker]), 1)
        self.assertEqual(monitor_fila.avisar([worker]), 0)  # mesmo problema: segura
        self.assertEqual(monitor_fila.avisar([monitor_fila.Problema('fila_indisponivel', 'x')]), 1)
        self.assertEqual(len(mail.outbox), 2)
        email = mail.outbox[0]
        self.assertEqual(email.to, [ADMIN])
        self.assertEqual(email.subject, '[Escala Connect] Celery: o worker do Celery não está rodando tarefas')
        self.assertIn('parado há 45 min', email.body)
        self.assertIn('docker compose logs', email.body)

    def test_volta_a_avisar_depois_da_janela(self):
        problema = monitor_fila.Problema('worker_parado', 'x')
        monitor_fila.avisar([problema])
        cache.delete(monitor_fila.PREFIXO_AVISO + 'worker_parado')  # a janela de 6 h passou
        monitor_fila.avisar([problema])
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(ADMINS=[])
    def test_sem_admins_so_registra_no_log(self):
        with self.assertLogs('escalaconnect.monitor_fila', 'ERROR') as logs:
            self.assertEqual(monitor_fila.avisar([monitor_fila.Problema('worker_parado', 'x')]), 0)
        self.assertEqual(mail.outbox, [])
        self.assertTrue(any('ADMINS vazio' in linha for linha in logs.output))

    def test_cache_fora_do_ar_nao_inunda(self):
        # Redis fora: a trava passa a ser por processo, ainda um e-mail por janela.
        problema = monitor_fila.Problema('fila_indisponivel', 'x')
        with mock.patch.object(cache, 'add', side_effect=OperationalError('sem redis')):
            monitor_fila.avisar([problema])
            monitor_fila.avisar([problema])
        self.assertEqual(len(mail.outbox), 1)

    def test_falha_no_smtp_nao_propaga(self):
        with mock.patch('escalaconnect.monitor_fila.mail_admins', side_effect=OSError('smtp fora')):
            monitor_fila.avisar([monitor_fila.Problema('worker_parado', 'x')])  # não levanta


class QuemEnfileiraTests(MonitorTestCase):
    """push.py e escala/fixa.py continuam engolindo o erro, mas agora avisam os admins."""

    def setUp(self):
        super().setUp()
        from api.models import Device
        from api.tests.test_conta import criar_usuario

        self.user = criar_usuario()
        Device.objects.create(usuario=self.user, expo_token='ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]',
                              plataforma='android')

    def notificar(self):
        from escalaconnect.push import notificar_push

        with self.captureOnCommitCallbacks(execute=True):
            notificar_push(self.user.pk, 'Título', 'Corpo', tipo='geral', purpose='confirm')

    def test_push_que_nao_entra_na_fila_avisa_uma_vez(self):
        from api.tasks import enviar_push_task

        with mock.patch.object(enviar_push_task, 'delay', side_effect=VersionMismatch('redis-py 5.3.1')), \
                self.assertLogs('escalaconnect.push', 'ERROR'):
            self.notificar()  # não vira erro para quem fez a ação
            self.notificar()
        (email,) = mail.outbox
        self.assertIn('a fila do Celery não aceita tarefas', email.subject)
        self.assertIn('Push: a tarefa não entrou na fila (VersionMismatch: redis-py 5.3.1)', email.body)

    def test_aviso_da_escala_fixa_que_nao_entra_na_fila_avisa(self):
        from api.tasks import avisar_escala_fixa_task
        from escala.fixa import _agendar_aviso

        with mock.patch.object(avisar_escala_fixa_task, 'apply_async', side_effect=OperationalError('sem redis')), \
                self.assertLogs('escala.fixa', 'ERROR'):
            _agendar_aviso(self.user.pk)
        (email,) = mail.outbox
        self.assertIn('Aviso da escala fixa: a tarefa não entrou na fila', email.body)

    def test_fila_aceita_mas_ninguem_consome(self):
        # Redis de pé, worker parado: o push entra na fila e não sai. A conferência pega.
        from api.tasks import enviar_push_task

        self.bater(worker_min=90, beat_min=90)
        with mock.patch.object(enviar_push_task, 'delay'):
            self.notificar()
            self.notificar()  # a conferência roda no máx. uma vez a cada 5 min
        (email,) = mail.outbox
        self.assertIn('o worker do Celery não está rodando tarefas', email.subject)
        self.assertIn('há 90 min', email.body)

    def test_fila_saudavel_nao_avisa(self):
        from api.tasks import enviar_push_task

        self.bater(worker_min=2, beat_min=2)
        with mock.patch.object(enviar_push_task, 'delay'):
            self.notificar()
        self.assertEqual(mail.outbox, [])


class SaudeCeleryEndpointTests(MonitorTestCase):
    def test_tudo_certo_responde_200(self):
        self.bater(worker_min=2, beat_min=2)
        resposta = self.client.get('/healthz/celery')
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.json()
        self.assertTrue(dados['ok'])
        self.assertTrue(dados['fila_aceita'])
        self.assertEqual(dados['problemas'], [])
        self.assertLessEqual(dados['worker_seg'], 1)  # o teste publicado (eager) já bateu
        self.assertEqual(mail.outbox, [])

    def test_com_e_sem_barra_sem_redirecionar(self):
        self.bater(worker_min=2, beat_min=2)
        for url in ('/healthz/celery', '/healthz/celery/'):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_fila_recusando_responde_503_e_avisa(self):
        self.bater(worker_min=2, beat_min=2)
        with mock.patch.object(batimento, 'apply_async', side_effect=VersionMismatch('redis-py 5.3.1')):
            resposta = self.client.get('/healthz/celery')
        self.assertEqual(resposta.status_code, 503)
        dados = resposta.json()
        self.assertFalse(dados['ok'])
        self.assertFalse(dados['fila_aceita'])
        self.assertEqual([p['codigo'] for p in dados['problemas']], ['fila_indisponivel'])
        self.assertEqual(len(mail.outbox), 1)

    def test_beat_parado_responde_503(self):
        self.bater(worker_min=2, beat_min=40)
        resposta = self.client.get('/healthz/celery')
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual([p['codigo'] for p in resposta.json()['problemas']], ['beat_parado'])

    def test_publica_no_maximo_um_teste_a_cada_30s(self):
        self.bater(worker_min=2, beat_min=2)
        with mock.patch.object(batimento, 'apply_async', side_effect=VersionMismatch('x')) as publicar:
            self.assertEqual(self.client.get('/healthz/celery').status_code, 503)
            # A segunda chamada não publica de novo, mas repete o último resultado.
            self.assertEqual(self.client.get('/healthz/celery').status_code, 503)
        publicar.assert_called_once()

    def test_so_get(self):
        self.assertEqual(self.client.post('/healthz/celery').status_code, 405)


class PaginaFilaTests(MonitorTestCase):
    """Monitoramento > Fila e push: só superusuário; agenda do beat, fila e últimos pushes."""

    URL = '/monitoramento/fila/'

    def setUp(self):
        super().setUp()
        from api.tests.test_conta import criar_usuario
        from evento.models import Notification, NotificationAttempt

        self.admin = criar_usuario(username='admin', cpf='39053344705', is_superuser=True, is_staff=True)
        self.voluntario = criar_usuario()
        notif = Notification.objects.create(
            usuario=self.voluntario, channel=Notification.CHANNEL_PUSH, purpose=Notification.PURPOSE_ASSIGNED)
        NotificationAttempt.objects.create(notification=notif, status='sent')
        NotificationAttempt.objects.create(notification=notif, status='error', error_message='DeviceNotRegistered')
        email = Notification.objects.create(usuario=self.voluntario, channel=Notification.CHANNEL_EMAIL)
        NotificationAttempt.objects.create(notification=email, status='sent')  # e-mail não entra

        # Sem broker nos testes: a fila e o worker são simulados.
        self.broker = {'fila': 'celery', 'total': 1, 'erro': None, 'proximas': [
            {'tarefa': 'api.tasks.enviar_push_task', 'id': 'x', 'args': "(7, 'Você foi escalado')",
             'eta': None, 'expira': None}]}
        self.worker = {'worker': 'celery@abc', 'rodando': [], 'reservadas': [], 'agendadas': [
            {'tarefa': 'api.tasks.verificar_recibos_push_task', 'id': 'y', 'args': "{'t1': 3}",
             'eta': None, 'inicio': None}]}
        for nome, valor in (('fila_no_broker', self.broker), ('tarefas_no_worker', self.worker)):
            patcher = mock.patch.object(monitor_fila, nome, return_value=valor)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_so_superusuario(self):
        self.assertEqual(self.client.get(self.URL).status_code, 302)  # anônimo vai para o login
        self.client.force_login(self.voluntario)
        self.assertEqual(self.client.get(self.URL).status_code, 403)

    def test_link_nas_abas_do_monitoramento(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/monitoramento/'), f'href="{self.URL}"')

    def test_mostra_agenda_fila_e_pushes(self):
        self.bater(worker_min=2, beat_min=2)
        self.client.force_login(self.admin)
        resposta = self.client.get(self.URL)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Tudo certo')
        # Beat: cada tarefa agendada, quando roda e a próxima execução.
        for tarefa in ('api.tasks.lembretes_de_escala', 'api.tasks.limpar_avisos_antigos',
                       'api.tasks.aplicar_escalas_fixas', 'escalaconnect.batimento'):
            self.assertContains(resposta, tarefa)
        self.assertContains(resposta, 'a cada 10 min')
        self.assertContains(resposta, 'todo dia às 03:30')
        agenda = {t['tarefa']: t for t in resposta.context['agenda']}
        proxima = agenda['api.tasks.limpar_avisos_antigos']['proxima']
        self.assertEqual((proxima.hour, proxima.minute), (3, 30))  # horário de Brasília
        # Fila: o que espera no broker e o que o worker tem agendado.
        self.assertContains(resposta, 'api.tasks.enviar_push_task')
        self.assertContains(resposta, 'api.tasks.verificar_recibos_push_task')
        # Pushes: só o canal push, com o erro da Expo.
        self.assertEqual(resposta.context['page_obj'].paginator.count, 2)
        self.assertEqual((resposta.context['enviados_24h'], resposta.context['erros_24h']), (1, 1))
        self.assertContains(resposta, 'DeviceNotRegistered')

    def test_filtro_de_situacao_do_push(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(self.URL, {'status': 'error'})
        self.assertEqual([a.status for a in resposta.context['page_obj']], ['error'])
        resposta = self.client.get(self.URL, {'status': 'qualquer'})  # valor inválido = todos
        self.assertEqual(resposta.context['page_obj'].paginator.count, 2)

    def test_problema_aparece_sem_mandar_email(self):
        self.bater(worker_min=60, beat_min=60)
        self.client.force_login(self.admin)
        with mock.patch.object(batimento, 'apply_async'):  # a fila aceita, mas ninguém roda o teste
            resposta = self.client.get(self.URL)
        self.assertContains(resposta, 'Com problema')
        self.assertContains(resposta, 'O worker do Celery não está rodando tarefas')
        self.assertEqual(mail.outbox, [])

    def test_worker_sem_resposta_e_problema_na_pagina(self):
        self.bater(worker_min=2, beat_min=2)  # batimento ainda recente
        monitor_fila.tarefas_no_worker.return_value = None
        self.client.force_login(self.admin)
        resposta = self.client.get(self.URL)
        self.assertContains(resposta, 'Com problema')
        self.assertContains(resposta, 'O worker não respondeu agora')
        self.assertEqual(mail.outbox, [])


class AgendaDoBeatTests(TestCase):
    def test_descricao_dos_horarios(self):
        from datetime import timedelta

        from celery.schedules import crontab

        self.assertEqual(monitor_fila._descrever_horario(crontab(minute='*/5')), 'a cada 5 min')
        self.assertEqual(monitor_fila._descrever_horario(crontab(hour=6, minute=0)), 'todo dia às 06:00')
        self.assertEqual(monitor_fila._descrever_horario(timedelta(minutes=30)), 'a cada 30 min')
        self.assertEqual(monitor_fila._descrever_horario(crontab(minute=0, hour=9, day_of_week=1)), 'cron 0 9 1 * *')

    def test_mensagem_crua_do_redis(self):
        import json

        bruta = json.dumps({'headers': {
            'task': 'api.tasks.enviar_push_task', 'id': 'abc', 'argsrepr': '(7,)', 'kwargsrepr': "{'tipo': 'x'}",
            'eta': '2026-11-14T15:00:00+00:00', 'expires': None}}).encode()
        resumo = monitor_fila._resumo_da_mensagem(bruta)
        self.assertEqual(resumo['tarefa'], 'api.tasks.enviar_push_task')
        self.assertEqual(resumo['args'], "(7,) {'tipo': 'x'}")
        self.assertEqual((resumo['eta'].hour, resumo['eta'].minute), (12, 0))  # 15:00 UTC = 12:00 local
        self.assertEqual(monitor_fila._resumo_da_mensagem(b'lixo')['tarefa'], '(mensagem ilegível)')
