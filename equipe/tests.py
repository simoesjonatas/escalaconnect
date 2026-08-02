from datetime import datetime, timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.timezone import now

from equipe.models import Equipe, Lideranca, MembrosEquipe
from evento.models import Evento
from escala.models import Funcao, Escala, Desistencia
from disponivel.models import Disponivel

User = get_user_model()


class DashboardLiderTests(TestCase):
    def test_dashboard_acessivel_para_lider_onboarded(self):
        equipe = Equipe.objects.create(nome="Louvor")
        lider = User.objects.create_user(
            username="lider",
            password="senha-teste",
            cpf="10000000500",
            is_first_login=False,      # passa pelo FirstLoginMiddleware
            termo_aceito_em=now(),     # passa pelo TermoVoluntarioMiddleware
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'equipe/dashboard_lider.html')

    def test_dashboard_mostra_disponiveis_nos_buracos(self):
        equipe = Equipe.objects.create(nome="Mídia")
        funcao = Funcao.objects.create(nome="Projeção", equipe=equipe)
        base = (now() + timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0)
        evento = Evento.objects.create(
            nome="Culto", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        Escala.objects.create(funcao=funcao, evento=evento)  # vaga em aberto

        vol = User.objects.create_user(
            username="voluntario_d", password="x", cpf="10000002001",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=vol, aprovado=True)
        Disponivel.objects.create(
            usuario=vol,
            data_inicio=base - timedelta(hours=1),
            data_fim=base + timedelta(hours=3),
        )

        lider = User.objects.create_user(
            username="lider2", password="x", cpf="10000002002",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "voluntario_d")  # o disponível aparece na coluna do painel

    def test_pendencias_so_de_eventos_futuros(self):
        equipe = Equipe.objects.create(nome="Diaconia P")
        funcao = Funcao.objects.create(nome="Porta", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_p", password="x", cpf="10000008001",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)
        vol = User.objects.create_user(
            username="vol_p", password="x", cpf="10000008002",
            is_first_login=False, termo_aceito_em=now(),
        )

        passado = Evento.objects.create(
            nome="Culto Passado",
            data_inicio=now() - timedelta(days=30),
            data_fim=now() - timedelta(days=30) + timedelta(hours=2),
        )
        futuro = Evento.objects.create(
            nome="Culto Futuro",
            data_inicio=now() + timedelta(days=5),
            data_fim=now() + timedelta(days=5) + timedelta(hours=2),
        )
        esc_passado = Escala.objects.create(usuario=vol, funcao=funcao, evento=passado, confirmada=True)
        esc_futuro = Escala.objects.create(usuario=vol, funcao=funcao, evento=futuro, confirmada=True)
        Desistencia.objects.create(escala=esc_passado, usuario=vol, motivo="x", aprovada=False)
        Desistencia.objects.create(escala=esc_futuro, usuario=vol, motivo="y", aprovada=False)

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Culto Futuro")        # pendência futura aparece
        self.assertNotContains(resp, "Culto Passado")    # pendência passada NÃO aparece

    def test_dashboard_lista_disponiveis_ociosos_do_mes(self):
        equipe = Equipe.objects.create(nome="Louvor Ocioso")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_o", password="x", cpf="10000009001",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        agora = now()

        def add_disp(u):
            # Cobre o mês atual e o evento futuro abaixo (para poder cobrir a vaga).
            Disponivel.objects.create(
                usuario=u, data_inicio=agora - timedelta(days=1), data_fim=agora + timedelta(days=3)
            )

        # Evento futuro com uma vaga em aberto — é o que dá "o que aproveitar".
        ev_futuro = Evento.objects.create(
            nome="Culto Futuro", data_inicio=agora + timedelta(days=2),
            data_fim=agora + timedelta(days=2, hours=2),
        )
        Escala.objects.create(funcao=funcao, evento=ev_futuro)  # vaga em aberto

        # ocioso: disponível, cobre a vaga futura e sem escala no mês.
        ocioso = User.objects.create_user(
            username="ocioso_vol", password="x", cpf="10000009002",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=ocioso, aprovado=True)
        add_disp(ocioso)

        # servido: disponível E já escalado neste mês -> não é ocioso.
        servido = User.objects.create_user(
            username="servido_vol", password="x", cpf="10000009003",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=servido, aprovado=True)
        add_disp(servido)
        ev = Evento.objects.create(
            nome="Culto do mês", data_inicio=agora, data_fim=agora + timedelta(hours=2)
        )
        Escala.objects.create(usuario=servido, funcao=funcao, evento=ev)

        # sem_disp: membro sem disponibilidade -> não cobre a vaga -> não aparece.
        sem_disp = User.objects.create_user(
            username="sem_disp_vol", password="x", cpf="10000009004",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=sem_disp, aprovado=True)

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['ociosos_total'], 1)
        nomes = [p.username for g in resp.context['disponiveis_ociosos'] for p in g['pessoas']]
        self.assertIn('ocioso_vol', nomes)
        self.assertNotIn('servido_vol', nomes)
        self.assertNotIn('sem_disp_vol', nomes)
        self.assertContains(resp, "Disponíveis ainda não escalados")

    def test_ocioso_recebe_atalho_para_proxima_vaga_em_aberto(self):
        equipe = Equipe.objects.create(nome="Louvor Atalho")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_at", password="x", cpf="10000009011",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)
        ocioso = User.objects.create_user(
            username="ocioso_at", password="x", cpf="10000009012",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=ocioso, aprovado=True)

        agora = now()
        # Disponibilidade ampla: cobre o mês atual e o evento futuro abaixo.
        Disponivel.objects.create(
            usuario=ocioso, data_inicio=agora - timedelta(days=1), data_fim=agora + timedelta(days=3)
        )
        evento = Evento.objects.create(
            nome="Culto Atalho",
            data_inicio=agora + timedelta(days=2),
            data_fim=agora + timedelta(days=2, hours=2),
        )
        vaga = Escala.objects.create(funcao=funcao, evento=evento)  # em aberto

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))
        self.assertEqual(resp.status_code, 200)
        pessoas = [p for g in resp.context['disponiveis_ociosos'] for p in g['pessoas']]
        alvo = next(p for p in pessoas if p.username == 'ocioso_at')
        self.assertIsNotNone(alvo.proxima_vaga)
        self.assertEqual(alvo.proxima_vaga.pk, vaga.pk)
        self.assertContains(resp, reverse('escala_detail', args=[vaga.pk]))

    def test_estado_positivo_quando_todos_disponiveis_ja_escalados(self):
        equipe = Equipe.objects.create(nome="Louvor Ok")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_ok", password="x", cpf="10000009021",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)
        vol = User.objects.create_user(
            username="vol_ok", password="x", cpf="10000009022",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=vol, aprovado=True)

        agora = now()
        Disponivel.objects.create(
            usuario=vol, data_inicio=agora - timedelta(days=1), data_fim=agora + timedelta(days=1)
        )
        ev = Evento.objects.create(
            nome="Culto OK", data_inicio=agora, data_fim=agora + timedelta(hours=2)
        )
        Escala.objects.create(usuario=vol, funcao=funcao, evento=ev)  # já escalado este mês

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['ociosos_total'], 0)
        self.assertTrue(resp.context['alguem_escalado_no_mes'])
        self.assertContains(resp, "já foram escalados este mês")

    def test_nao_lista_quem_so_tem_disponibilidade_passada(self):
        # Regressão: hoje é dia X, a pessoa só se disponibilizou para dias já
        # passados — não dá mais para aproveitá-la, então não deve aparecer.
        equipe = Equipe.objects.create(nome="Louvor Passado")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_pass", password="x", cpf="10000009031",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)
        vol = User.objects.create_user(
            username="vol_passado", password="x", cpf="10000009032",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=vol, aprovado=True)

        agora = now()
        # Disponibilidade só no passado.
        Disponivel.objects.create(
            usuario=vol, data_inicio=agora - timedelta(days=5), data_fim=agora - timedelta(days=3)
        )
        # Existe vaga futura em aberto, mas ele não cobre (disponibilidade passada).
        ev_futuro = Evento.objects.create(
            nome="Culto Futuro P", data_inicio=agora + timedelta(days=2),
            data_fim=agora + timedelta(days=2, hours=2),
        )
        Escala.objects.create(funcao=funcao, evento=ev_futuro)

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['ociosos_total'], 0)
        self.assertNotContains(resp, "vol_passado")

    def test_nao_lista_equipe_sem_vaga_futura_em_aberto(self):
        # Regressão: a pessoa é de uma equipe (ex.: Fotografia) que não tem
        # nenhum evento/função em aberto daqui pra frente — não há como usá-la.
        equipe = Equipe.objects.create(nome="Fotografia")
        Funcao.objects.create(nome="Foto", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_foto", password="x", cpf="10000009041",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)
        foto_vol = User.objects.create_user(
            username="foto_vol", password="x", cpf="10000009042",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=foto_vol, aprovado=True)

        agora = now()
        # Disponibilidade ampla e futura, mas não há NENHUMA vaga de fotografia.
        Disponivel.objects.create(
            usuario=foto_vol, data_inicio=agora - timedelta(days=1), data_fim=agora + timedelta(days=10)
        )

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['ociosos_total'], 0)
        self.assertNotContains(resp, "foto_vol")

    def test_lista_ocioso_que_pode_substituir_escala_nao_confirmada(self):
        # Y já atuou este mês e ainda ocupa uma escala futura NÃO confirmada;
        # X está ocioso e disponível -> X deve ser sugerido para o lugar de Y.
        equipe = Equipe.objects.create(nome="Louvor Troca")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_troca", password="x", cpf="10000009051",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        agora = now()
        y = User.objects.create_user(
            username="y_serviu", password="x", cpf="10000009052",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=y, aprovado=True)
        # Y já atuou este mês.
        ev_mes = Evento.objects.create(
            nome="Culto Y no mes", data_inicio=agora, data_fim=agora + timedelta(hours=1)
        )
        Escala.objects.create(usuario=y, funcao=funcao, evento=ev_mes)
        # Y também ocupa uma escala futura, ainda não confirmada.
        ev_futuro = Evento.objects.create(
            nome="Culto Futuro Troca", data_inicio=agora + timedelta(days=2),
            data_fim=agora + timedelta(days=2, hours=2),
        )
        escala_y_futura = Escala.objects.create(
            usuario=y, funcao=funcao, evento=ev_futuro, confirmada=False
        )

        # X ocioso, disponível para o evento futuro.
        x = User.objects.create_user(
            username="x_disponivel", password="x", cpf="10000009053",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=x, aprovado=True)
        Disponivel.objects.create(
            usuario=x, data_inicio=agora - timedelta(days=1), data_fim=agora + timedelta(days=3)
        )

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))
        self.assertEqual(resp.status_code, 200)
        pessoas = {p.username: p for g in resp.context['disponiveis_ociosos'] for p in g['pessoas']}
        self.assertIn('x_disponivel', pessoas)
        self.assertEqual(pessoas['x_disponivel'].proxima_vaga.pk, escala_y_futura.pk)
        # a oportunidade é uma troca (a vaga tem ocupante)
        self.assertIsNotNone(pessoas['x_disponivel'].proxima_vaga.usuario)
        self.assertNotIn('y_serviu', pessoas)  # Y já serviu -> não é ocioso

    def test_nao_sugere_substituir_escala_confirmada(self):
        equipe = Equipe.objects.create(nome="Louvor Confirmada")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        lider = User.objects.create_user(
            username="lider_conf", password="x", cpf="10000009061",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        agora = now()
        y = User.objects.create_user(
            username="y_confirmou", password="x", cpf="10000009062",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=y, aprovado=True)
        ev_mes = Evento.objects.create(
            nome="Culto Y conf mes", data_inicio=agora, data_fim=agora + timedelta(hours=1)
        )
        Escala.objects.create(usuario=y, funcao=funcao, evento=ev_mes)
        ev_futuro = Evento.objects.create(
            nome="Culto Futuro Conf", data_inicio=agora + timedelta(days=2),
            data_fim=agora + timedelta(days=2, hours=2),
        )
        # Escala futura de Y JÁ CONFIRMADA -> não deve virar sugestão de troca.
        Escala.objects.create(
            usuario=y, funcao=funcao, evento=ev_futuro,
            confirmada=True, data_confirmacao=agora,
        )

        x = User.objects.create_user(
            username="x_conf", password="x", cpf="10000009063",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=x, aprovado=True)
        Disponivel.objects.create(
            usuario=x, data_inicio=agora - timedelta(days=1), data_fim=agora + timedelta(days=3)
        )

        self.client.force_login(lider)
        resp = self.client.get(reverse('dashboard_lider'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['ociosos_total'], 0)
        self.assertNotContains(resp, "x_conf")


class HomeAvisoMembrosPendentesTests(TestCase):
    def test_lider_ve_aviso_de_pedido_de_entrada(self):
        equipe = Equipe.objects.create(nome="Diaconia")
        lider = User.objects.create_user(
            username="lid", password="x", cpf="10000005001",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=lider, equipe=equipe)

        cand = User.objects.create_user(
            username="cand", password="x", cpf="10000005002",
            is_first_login=False, termo_aceito_em=now(),
        )
        MembrosEquipe.objects.create(equipe=equipe, usuario=cand, aprovado=False)

        self.client.force_login(lider)
        resp = self.client.get('/')
        self.assertContains(resp, "querendo entrar nas suas equipes")
        self.assertContains(resp, "Diaconia")


class LembreteDisponibilidadePermissaoTests(TestCase):
    """O líder (não-staff) precisa conseguir disparar o lembrete sem cair em 403.

    Regressão: a rota usa o kwarg `equipe_id`, mas o decorator só olhava
    `equipe_pk`/`pk`, barrando o líder comum.
    """

    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Louvor Lembrete")
        self.lider = User.objects.create_user(
            username="lider_lembrete", password="x", cpf="10000009001",
            is_first_login=False, termo_aceito_em=now(),
        )
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)

    @patch('equipe.views_escala.disparar_pedido_disponibilidades.delay')
    def test_lider_dispara_lembrete_sem_403(self, mock_delay):
        self.client.force_login(self.lider)
        resp = self.client.post(
            reverse('lider_pedir_disponibilidades', kwargs={'equipe_id': self.equipe.pk}),
            {'ano': now().year, 'mes': now().month},
        )
        self.assertEqual(resp.status_code, 302)            # redirect, não 403
        mock_delay.assert_called_once()
        self.assertEqual(mock_delay.call_args.kwargs.get('equipe_id'), self.equipe.pk)

    @patch('equipe.views_escala.disparar_pedido_disponibilidades.delay')
    def test_nao_lider_recebe_403(self, mock_delay):
        estranho = User.objects.create_user(
            username="estranho_lembrete", password="x", cpf="10000009002",
            is_first_login=False, termo_aceito_em=now(),
        )
        self.client.force_login(estranho)
        resp = self.client.post(
            reverse('lider_pedir_disponibilidades', kwargs={'equipe_id': self.equipe.pk}),
            {'ano': now().year, 'mes': now().month},
        )
        self.assertEqual(resp.status_code, 403)
        mock_delay.assert_not_called()


class DispararPedidoDisponibilidadesTaskTests(TestCase):
    """A task notifica só os membros aprovados que ainda NÃO têm disponibilidade no mês."""

    def setUp(self):
        hoje = now().date()
        self.ano = hoje.year + (1 if hoje.month == 12 else 0)
        self.mes = 1 if hoje.month == 12 else hoje.month + 1

        self.equipe = Equipe.objects.create(nome="Equipe Task")
        Funcao.objects.create(nome="Vocal", equipe=self.equipe)

        # Evento dentro do mês alvo (senão a task aborta com "sem eventos no mês").
        ini = timezone.make_aware(datetime(self.ano, self.mes, 15, 10, 0))
        Evento.objects.create(
            nome="Culto Task", data_inicio=ini, data_fim=ini + timedelta(hours=2),
        )

        # Pendente: aprovado, com e-mail, SEM disponibilidade no mês -> deve receber.
        self.pendente = User.objects.create_user(
            username="pendente_task", password="x", cpf="10000009101",
            email="pendente@example.com",
        )
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=self.pendente, aprovado=True)

        # Em dia: aprovado, com e-mail, COM disponibilidade no mês -> NÃO deve receber.
        self.em_dia = User.objects.create_user(
            username="em_dia_task", password="x", cpf="10000009102",
            email="emdia@example.com",
        )
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=self.em_dia, aprovado=True)
        Disponivel.objects.create(
            usuario=self.em_dia,
            data_inicio=timezone.make_aware(datetime(self.ano, self.mes, 14, 8, 0)),
            data_fim=timezone.make_aware(datetime(self.ano, self.mes, 16, 22, 0)),
        )

    def test_envia_so_para_quem_nao_tem_disponibilidade(self):
        from escalaconnect.tasks_availability import disparar_pedido_disponibilidades
        resultado = disparar_pedido_disponibilidades(
            ano=self.ano, mes=self.mes, equipe_id=self.equipe.pk, lider_nome="Líder Teste",
        )
        destinatarios = [addr for m in mail.outbox for addr in m.to]
        self.assertIn("pendente@example.com", destinatarios)
        self.assertNotIn("emdia@example.com", destinatarios)
        self.assertEqual(resultado.get("emails_enviados"), 1)
