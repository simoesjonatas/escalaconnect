"""Fluxos do voluntário no site que passaram a usar escala/services.py."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Equipe, Lideranca
from escala.models import Desistencia, Escala, Funcao, SolicitacaoTroca
from evento.models import Evento

User = get_user_model()


def criar_voluntario(username, cpf):
    return User.objects.create_user(
        username=username, password='x', cpf=cpf, email=f'{username}@example.com',
        is_first_login=False, termo_aceito_em=timezone.now(),
    )


class FluxosDoVoluntarioNoSiteTests(TestCase):
    def setUp(self):
        self.equipe = Equipe.objects.create(nome='Recepção')
        self.funcao = Funcao.objects.create(nome='Porta', equipe=self.equipe)
        self.user = criar_voluntario('maria', '52998224725')
        self.outro = criar_voluntario('joao', '11144477735')
        self.lider = criar_voluntario('lider', '39053344705')
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)
        self.escala = self.criar_escala(self.user, dias=3)
        self.client.force_login(self.user)

    def criar_escala(self, usuario, dias):
        inicio = timezone.now() + timedelta(days=dias)
        evento = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        return Escala.objects.create(usuario=usuario, funcao=self.funcao, evento=evento)

    def mensagens(self, resp):
        return [str(m) for m in get_messages(resp.wsgi_request)]

    def test_confirmar_por_post(self):
        resp = self.client.post(reverse('confirmar_minha_escala', args=[self.escala.pk]))
        self.assertRedirects(resp, reverse('minha_escala_detail', args=[self.escala.pk]))
        self.escala.refresh_from_db()
        self.assertTrue(self.escala.confirmada)
        self.assertIn("Escala confirmada com sucesso!", self.mensagens(resp))

    def test_get_nao_confirma(self):
        self.client.get(reverse('confirmar_minha_escala', args=[self.escala.pk]))
        self.escala.refresh_from_db()
        self.assertFalse(self.escala.confirmada)

    def test_nao_confirma_escala_de_outro(self):
        alheia = self.criar_escala(self.outro, dias=3)
        resp = self.client.post(reverse('confirmar_minha_escala', args=[alheia.pk]))
        self.assertRedirects(resp, reverse('minhas_escalas'))
        alheia.refresh_from_db()
        self.assertFalse(alheia.confirmada)

    def test_nao_confirma_evento_encerrado(self):
        passada = self.criar_escala(self.user, dias=-2)
        resp = self.client.post(reverse('confirmar_minha_escala', args=[passada.pk]))
        passada.refresh_from_db()
        self.assertFalse(passada.confirmada)
        self.assertIn("Você não pode confirmar uma escala de um evento já encerrado.", self.mensagens(resp))

    def test_sinalizar_impedimento_cria_desistencia_uma_vez(self):
        url = reverse('sinalizar_impedimento', args=[self.escala.pk])
        resp = self.client.post(url, {'motivo': 'Viagem'})
        self.assertRedirects(resp, reverse('minhas_escalas'))
        resp = self.client.post(url, {'motivo': 'De novo'})
        self.assertContains(resp, "Você já sinalizou desistência para esta escala.")
        self.assertEqual(Desistencia.objects.filter(escala=self.escala, usuario=self.user).count(), 1)

    def test_impedimento_em_escala_de_outro_e_recusado(self):
        alheia = self.criar_escala(self.outro, dias=3)
        resp = self.client.post(reverse('sinalizar_impedimento', args=[alheia.pk]), {'motivo': 'x'})
        # 404, que o handler404 do site transforma em redirecionamento para a home.
        self.assertRedirects(resp, '/', fetch_redirect_response=False)
        self.assertFalse(Desistencia.objects.exists())

    def test_lider_aprova_desistencia_e_libera_a_vaga(self):
        desistencia = Desistencia.objects.create(escala=self.escala, usuario=self.user, motivo='Viagem')
        self.client.force_login(self.lider)
        self.client.post(reverse('aprovar_desistencia', args=[desistencia.pk]))
        desistencia.refresh_from_db()
        self.escala.refresh_from_db()
        self.assertTrue(desistencia.aprovada)
        self.assertIsNone(self.escala.usuario)

    def test_pedir_cancelar_e_aprovar_troca(self):
        pedir = reverse('solicitar_desistencia', args=[self.escala.pk])
        self.client.post(pedir, {'tipo_solicitacao': 'desistencia'})
        self.client.post(pedir, {'tipo_solicitacao': 'desistencia'})  # repetido: recusado
        self.assertEqual(SolicitacaoTroca.objects.filter(escala_origem=self.escala).count(), 1)

        self.client.get(reverse('cancelar_solicitacao_troca', args=[self.escala.pk]))
        self.assertFalse(SolicitacaoTroca.objects.exists())

        self.client.post(pedir, {'tipo_solicitacao': 'desistencia'})
        troca = SolicitacaoTroca.objects.get()
        self.client.force_login(self.lider)
        self.client.post(reverse('aprovar_solicitacao_troca', args=[troca.pk]))
        troca.refresh_from_db()
        self.escala.refresh_from_db()
        self.assertTrue(troca.aprovada)
        self.assertEqual(troca.lider_aprovador, self.lider)
        self.assertIsNone(self.escala.usuario)


class TirarDaEscalaPelaEquipeTests(TestCase):
    """Botão "Tirar da escala" no detalhe da escala por equipe, antes ou depois da confirmação."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome='Recepção')
        self.funcao = Funcao.objects.create(nome='Porta', equipe=self.equipe)
        self.voluntario = criar_voluntario('maria', '52998224725')
        self.lider = criar_voluntario('lider', '39053344705')
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)
        inicio = timezone.now() + timedelta(days=3)
        evento = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        self.escala = Escala.objects.create(usuario=self.voluntario, funcao=self.funcao, evento=evento)
        self.detalhe = reverse('escala_detail_equipe', args=[self.equipe.pk, self.escala.pk])
        self.cancelar = reverse('cancelar_escala_equipe', args=[self.escala.pk])

    def test_lider_ve_o_botao_antes_da_confirmacao_e_tira_a_pessoa(self):
        self.client.force_login(self.lider)
        self.assertContains(self.client.get(self.detalhe), 'Tirar da escala')
        resp = self.client.get(self.cancelar)
        self.assertRedirects(resp, self.detalhe)
        self.escala.refresh_from_db()
        self.assertIsNone(self.escala.usuario)
        self.assertNotContains(self.client.get(self.detalhe), 'Tirar da escala')

    def test_voluntario_comum_nao_tira(self):
        self.client.force_login(self.voluntario)
        self.client.get(self.cancelar)
        self.escala.refresh_from_db()
        self.assertEqual(self.escala.usuario, self.voluntario)
