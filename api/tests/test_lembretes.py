"""Lembrete de disponibilidade (e-mail e/ou app) e aviso pelo app 2 horas antes do evento."""
from datetime import timedelta

from django.contrib.messages import get_messages
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from api.models import Device
from api.tasks import lembrar_escalas_proximas
from equipe.models import Lideranca, MembrosEquipe
from escala.models import Escala
from escalaconnect.tasks_availability import disparar_pedido_disponibilidades
from evento.models import Evento, Notification

from .test_conta import criar_usuario
from .test_push import OUTRO_TOKEN, PushTestCase


class AvisoAntesDoEventoTests(PushTestCase):
    """lembrar_escalas_proximas: um push por escala, só para eventos que começam em até 2 horas."""

    def escalar(self, horas, usuario=None, nome='Culto da noite', **extra):
        inicio = timezone.now() + timedelta(hours=horas)
        evento = Evento.objects.create(nome=nome, data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        return Escala.objects.create(usuario=usuario or self.user, funcao=self.funcao, evento=evento, **extra)

    def rodar(self):
        with self.captureOnCommitCallbacks(execute=True):
            resultado = lembrar_escalas_proximas()
        return resultado

    def avisos(self):
        return [m for m in self.mensagens() if m['title'].startswith('Você serve')]

    def test_avisa_so_eventos_dentro_da_janela(self):
        proxima = self.escalar(1)
        self.escalar(3, nome='Mais tarde')
        self.escalar(-1, nome='Já começou')
        self.post.reset_mock()  # descarta os pushes "Você foi escalado" da criação

        self.assertEqual(self.rodar(), 1)
        (msg,) = self.avisos()
        self.assertIn('Culto da noite', msg['body'])
        self.assertIn('Porta', msg['body'])
        self.assertIn('Confirme sua presença', msg['body'])  # ainda não confirmou
        self.assertEqual(msg['data'], {'tipo': 'escalado', 'escala_id': proxima.pk})  # o app abre a escala
        self.assertEqual(mail.outbox, [])  # este aviso é só pelo app

    def test_confirmado_nao_recebe_pedido_de_confirmacao(self):
        self.escalar(1, confirmada=True)
        self.post.reset_mock()
        self.rodar()
        (msg,) = self.avisos()
        self.assertNotIn('Confirme', msg['body'])

    def test_rodar_de_novo_nao_repete(self):
        self.escalar(1)
        self.post.reset_mock()
        self.assertEqual(self.rodar(), 1)
        self.assertEqual(self.rodar(), 0)
        self.assertEqual(self.rodar(), 0)
        self.assertEqual(len(self.avisos()), 1)
        notif = Notification.objects.get(purpose=Notification.PURPOSE_EVENT_SOON)
        self.assertEqual((notif.channel, notif.success_count), (Notification.CHANNEL_PUSH, 1))

    def test_quem_nao_tem_o_app_nao_gera_envio(self):
        self.escalar(1, usuario=criar_usuario(username='joao', cpf='11144477735'))
        self.post.reset_mock()
        self.assertEqual(self.rodar(), 0)
        self.post.assert_not_called()

    def test_troca_de_voluntario_avisa_o_novo(self):
        escala = self.escalar(1)
        self.post.reset_mock()
        self.rodar()

        outro = criar_usuario(username='joao', cpf='11144477735')
        Device.objects.create(usuario=outro, expo_token=OUTRO_TOKEN, plataforma='ios')
        escala.usuario = outro
        escala.save()
        self.post.reset_mock()
        self.assertEqual(self.rodar(), 1)
        (msg,) = self.avisos()
        self.assertEqual(msg['to'], OUTRO_TOKEN)

    @override_settings(LEMBRETE_EVENTO_HORAS=4)
    def test_antecedencia_configuravel(self):
        self.escalar(3)
        self.post.reset_mock()
        self.assertEqual(self.rodar(), 1)


class LembreteDeDisponibilidadeTests(PushTestCase):
    """Os dois botões do líder: e-mail + app, ou só app."""

    def setUp(self):
        super().setUp()
        hoje = timezone.localdate()
        self.ano, self.mes = (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)
        inicio = timezone.make_aware(timezone.datetime(self.ano, self.mes, 15, 19, 0))
        Evento.objects.create(nome='Culto do mês', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        MembrosEquipe.objects.create(usuario=self.user, equipe=self.equipe, aprovado=True)  # tem app e e-mail
        self.sem_app = criar_usuario(username='joao', cpf='11144477735')                    # só e-mail
        MembrosEquipe.objects.create(usuario=self.sem_app, equipe=self.equipe, aprovado=True)
        self.lider = criar_usuario(username='lider', cpf='39053344705')
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)
        self.url = reverse('lider_pedir_disponibilidades', kwargs={'equipe_id': self.equipe.pk})
        self.post.reset_mock()

    def disparar(self, **extra):
        with self.captureOnCommitCallbacks(execute=True):
            return disparar_pedido_disponibilidades(ano=self.ano, mes=self.mes, equipe_id=self.equipe.pk, **extra)

    def test_padrao_manda_email_e_push(self):
        resultado = self.disparar()
        self.assertEqual(resultado['emails_enviados'], 2)
        self.assertEqual(resultado['push_enfileirados'], 1)
        self.assertEqual([m['title'] for m in self.mensagens()], ['Informe sua disponibilidade'])
        self.assertEqual(self.mensagens()[0]['data']['tipo'], 'disponibilidade')

    def test_so_app_nao_manda_email(self):
        resultado = self.disparar(canais=['push'])
        self.assertEqual(mail.outbox, [])
        self.assertEqual(resultado['emails_enviados'], 0)
        self.assertEqual(resultado['push_enfileirados'], 1)
        self.assertEqual(resultado['usuarios_faltantes'], 2)
        self.assertEqual(len(self.mensagens()), 1)

    def test_botao_so_app_pelo_site(self):
        self.client.force_login(self.lider)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(self.url, {'ano': self.ano, 'mes': self.mes, 'canal': 'app'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(self.mensagens()), 1)
        texto = ' '.join(str(m) for m in get_messages(resp.wsgi_request))
        self.assertIn('1 notificação(ões) no app', texto)
        self.assertNotIn('e-mail', texto)

    def test_botao_email_e_app_pelo_site(self):
        self.client.force_login(self.lider)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(self.url, {'ano': self.ano, 'mes': self.mes, 'canal': 'todos'})
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(len(self.mensagens()), 1)
        texto = ' '.join(str(m) for m in get_messages(resp.wsgi_request))
        self.assertIn('2 e-mail(s) e 1 notificação(ões) no app', texto)

    def test_pagina_mostra_os_dois_botoes(self):
        self.client.force_login(self.lider)
        resp = self.client.get(reverse('disponibilidades_equipe', kwargs={'equipe_pk': self.equipe.pk}))
        self.assertContains(resp, 'Enviar lembrete (e-mail e app)')
        self.assertContains(resp, 'Lembrar só pelo app')

    def test_voluntario_comum_nao_dispara(self):
        self.client.force_login(self.sem_app)
        resp = self.client.post(self.url, {'ano': self.ano, 'mes': self.mes, 'canal': 'app'})
        self.assertEqual(resp.status_code, 403)
        self.post.assert_not_called()
