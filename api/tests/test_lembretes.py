"""Lembrete de disponibilidade (e-mail e/ou app) e lembretes de escala pelo app."""
from datetime import datetime, timedelta
from unittest import mock

from django.contrib.messages import get_messages
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from api.models import Device
from api.tasks import lembretes_de_escala
from equipe.models import Lideranca, MembrosEquipe
from escala.models import Escala
from escalaconnect.tasks_availability import disparar_pedido_disponibilidades
from evento.models import Evento, Notification

from .test_conta import criar_usuario
from .test_push import OUTRO_TOKEN, PushTestCase


def local(dia, hora, minuto=0):
    """Horário local em outubro de 2026 (25/10 é domingo)."""
    return timezone.make_aware(datetime(2026, 10, dia, hora, minuto))


class LembretesDeEscalaTests(PushTestCase):
    """lembretes_de_escala: véspera/dia conforme o horário do culto; cobrança só para quem não confirmou."""

    def setUp(self):
        super().setUp()
        self.escala.delete()  # a escala da base fica em "agora + 3 dias", fora do relógio destes testes

    def escalar(self, inicio, usuario=None, nome='Culto da noite', **extra):
        evento = Evento.objects.create(nome=nome, data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        escala = Escala.objects.create(usuario=usuario or self.user, funcao=self.funcao, evento=evento, **extra)
        self.post.reset_mock()  # descarta o "Você foi escalado" da criação
        return escala

    def rodar(self, agora):
        """Roda a task com o relógio em `agora` e devolve as mensagens enviadas nesta rodada."""
        self.post.reset_mock()
        with mock.patch('django.utils.timezone.now', return_value=agora), \
                self.captureOnCommitCallbacks(execute=True):
            lembretes_de_escala()
        return self.mensagens()

    def titulos(self, agora):
        return [m['title'] for m in self.rodar(agora)]

    def test_culto_da_manha_confirmado_lembra_na_vespera_as_20h(self):
        escala = self.escalar(local(25, 9, 45), nome='Culto da manhã', confirmada=True)
        self.assertEqual(self.rodar(local(24, 19, 50)), [])
        (msg,) = self.rodar(local(24, 20, 0))
        self.assertEqual(msg['title'], 'Amanhã é dia de servir 💚')
        self.assertEqual(msg['body'], 'Culto da manhã · 09:45 · Porta')
        self.assertEqual(msg['data'], {'tipo': 'escalado', 'escala_id': escala.pk, 'evento_id': escala.evento_id})  # o app abre a escala
        self.assertEqual(self.rodar(local(24, 20, 10)), [])  # não repete
        self.assertEqual(self.rodar(local(25, 7, 50)), [])   # confirmado não tem última chamada
        self.assertEqual(mail.outbox, [])  # só pelo app

    def test_culto_da_noite_confirmado_lembra_no_dia_ao_meio_dia(self):
        self.escalar(local(25, 19, 30), confirmada=True)
        self.assertEqual(self.rodar(local(24, 20, 0)), [])
        (msg,) = self.rodar(local(25, 12, 0))
        self.assertEqual((msg['title'], msg['body']), ('Hoje você serve às 19:30 💚', 'Culto da noite · Porta'))
        self.assertEqual(self.rodar(local(25, 17, 40)), [])

    def test_nao_confirmado_culto_da_manha(self):
        self.escalar(local(25, 9, 45), nome='Culto da manhã')
        self.assertEqual(self.rodar(local(24, 17, 50)), [])
        (msg,) = self.rodar(local(24, 18, 0))
        self.assertEqual((msg['title'], msg['body']), ('Confirma sua escala?', 'Culto da manhã · amanhã, 09:45 · Porta'))
        self.assertEqual(self.rodar(local(24, 20, 0)), [])  # quem recebeu o pedido das 18h não recebe o das 20h
        (msg,) = self.rodar(local(25, 7, 45))
        self.assertEqual(msg['title'], 'Sua escala começa às 09:45')
        self.assertIn('confirmar', msg['body'])

    def test_nao_confirmado_culto_da_noite(self):
        self.escalar(local(25, 19, 30))
        self.assertEqual(self.titulos(local(24, 18, 0)), ['Confirma sua escala?'])
        (msg,) = self.rodar(local(25, 12, 0))
        self.assertEqual((msg['title'], msg['body']), ('Hoje você serve às 19:30', 'Culto da noite · toque para confirmar'))
        self.assertEqual(self.titulos(local(25, 17, 30)), ['Sua escala começa às 19:30'])
        self.assertEqual(self.rodar(local(25, 18, 0)), [])

    def test_quem_confirma_depois_do_pedido_recebe_so_lembrete_amigavel(self):
        escala = self.escalar(local(25, 9, 45), nome='Culto da manhã')
        self.assertEqual(self.titulos(local(24, 18, 0)), ['Confirma sua escala?'])
        escala.confirmada = True
        escala.save()
        self.assertEqual(self.titulos(local(24, 20, 0)), ['Amanhã é dia de servir 💚'])
        self.assertEqual(self.rodar(local(25, 7, 45)), [])

    def test_quem_confirmou_nunca_recebe_cobranca(self):
        self.escalar(local(25, 9, 45), nome='Culto da manhã', confirmada=True)
        self.escalar(local(25, 19, 30), confirmada=True)
        mensagens = []
        for agora in (local(24, 18, 0), local(24, 20, 0), local(25, 7, 45), local(25, 12, 0), local(25, 17, 30)):
            mensagens += self.rodar(agora)
        self.assertEqual(len(mensagens), 2)
        for msg in mensagens:
            self.assertNotIn('confirm', f"{msg['title']} {msg['body']}".lower())

    def test_beat_parado_manda_so_o_aviso_mais_recente(self):
        self.escalar(local(25, 19, 30))
        self.assertEqual(self.titulos(local(25, 17, 40)), ['Sua escala começa às 19:30'])
        self.assertEqual(self.rodar(local(25, 17, 50)), [])

    def test_aviso_da_vespera_atrasado_diz_hoje(self):
        self.escalar(local(25, 9, 45), nome='Culto da manhã', confirmada=True)
        self.assertEqual(self.titulos(local(25, 0, 10)), ['Hoje você serve às 09:45 💚'])

    def test_quem_nao_tem_o_app_nao_gera_envio(self):
        self.escalar(local(25, 19, 30), usuario=criar_usuario(username='joao', cpf='11144477735'))
        self.assertEqual(self.rodar(local(25, 12, 0)), [])

    def test_troca_de_voluntario_avisa_o_novo(self):
        escala = self.escalar(local(25, 19, 30), confirmada=True)
        self.rodar(local(25, 12, 0))
        outro = criar_usuario(username='joao', cpf='11144477735')
        Device.objects.create(usuario=outro, expo_token=OUTRO_TOKEN, plataforma='ios')
        escala.usuario = outro
        escala.save()
        (msg,) = self.rodar(local(25, 12, 10))
        self.assertEqual(msg['to'], OUTRO_TOKEN)
        notif = Notification.objects.get(usuario=self.user, purpose=Notification.PURPOSE_DAY_REMINDER)
        self.assertEqual((notif.channel, notif.success_count), (Notification.CHANNEL_PUSH, 1))

    @override_settings(LEMBRETE_DIA_HORA=10, LEMBRETE_EVENTO_HORAS=4)
    def test_horarios_configuraveis(self):
        self.escalar(local(25, 19, 30))
        self.assertEqual(self.titulos(local(25, 10, 0)), ['Hoje você serve às 19:30'])
        self.assertEqual(self.titulos(local(25, 15, 30)), ['Sua escala começa às 19:30'])


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
        self.assertEqual([m['title'] for m in self.mensagens()], ['Quando você pode servir?'])
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
