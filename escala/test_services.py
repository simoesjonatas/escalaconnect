"""Fluxos do voluntário no site que passaram a usar escala/services.py."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Equipe, Lideranca, MembrosEquipe
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
        MembrosEquipe.objects.create(usuario=self.voluntario, equipe=self.equipe, aprovado=True)
        inicio = timezone.now() + timedelta(days=3)
        evento = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        self.escala = Escala.objects.create(usuario=self.voluntario, funcao=self.funcao, evento=evento)
        self.detalhe = reverse('escala_detail_equipe', args=[self.equipe.pk, self.escala.pk])
        self.cancelar = reverse('cancelar_escala_equipe', args=[self.escala.pk])

    def test_lider_ve_o_botao_antes_da_confirmacao_e_tira_a_pessoa(self):
        self.client.force_login(self.lider)
        resp = self.client.get(self.detalhe)
        self.assertContains(resp, 'Tirar da escala')
        self.assertContains(resp, 'id="buscaMembro"')  # busca de membro no modal
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


class VagasAbertasNoSiteTests(TestCase):
    """Página "Vagas em aberto" e cartão no Início: mesma regra do app (vaga some só quando alguém é escalado)."""

    def setUp(self):
        from disponivel.models import Disponivel
        self.user = criar_voluntario('maria', '52998224725')
        self.recepcao = Equipe.objects.create(nome='Recepção')
        self.louvor = Equipe.objects.create(nome='Louvor')
        for equipe in (self.recepcao, self.louvor):
            MembrosEquipe.objects.create(usuario=self.user, equipe=equipe, aprovado=True)
        inicio = timezone.now() + timedelta(days=5)
        self.culto = Evento.objects.create(nome='Culto', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        self.vaga_recepcao = Escala.objects.create(funcao=Funcao.objects.create(nome='Porta', equipe=self.recepcao), evento=self.culto)
        self.vaga_louvor = Escala.objects.create(funcao=Funcao.objects.create(nome='Vocal', equipe=self.louvor), evento=self.culto)
        # Na Recepção alguém já está disponível, mas a vaga continua aparecendo até ser preenchida.
        self.outro = criar_voluntario('joao', '11144477735')
        MembrosEquipe.objects.create(usuario=self.outro, equipe=self.recepcao, aprovado=True)
        Disponivel.objects.create(usuario=self.outro, evento=self.culto, data_inicio=self.culto.data_inicio, data_fim=self.culto.data_fim)
        self.client.force_login(self.user)

    def preencher_recepcao(self):
        self.vaga_recepcao.usuario = self.outro
        self.vaga_recepcao.save()

    def test_vaga_com_alguem_disponivel_continua_na_lista(self):
        resp = self.client.get(reverse('vagas_abertas'))
        self.assertEqual({v.pk for v in resp.context['page_obj']}, {self.vaga_recepcao.pk, self.vaga_louvor.pk})
        self.assertContains(self.client.get('/'), 'Sua equipe precisa de ajuda')

    def test_filtro_so_com_equipes_que_tem_vaga(self):
        resp = self.client.get(reverse('vagas_abertas'))
        self.assertContains(resp, 'aria-label="Filtrar por equipe"')
        resp = self.client.get(reverse('vagas_abertas'), {'equipe': self.louvor.pk})
        self.assertEqual([v.pk for v in resp.context['page_obj']], [self.vaga_louvor.pk])

        self.preencher_recepcao()  # escalado: a vaga some, e com uma equipe só não há filtro
        resp = self.client.get(reverse('vagas_abertas'))
        self.assertEqual([v.pk for v in resp.context['page_obj']], [self.vaga_louvor.pk])
        self.assertEqual(resp.context['equipes'], [(self.louvor.pk, 'Louvor', 1)])
        self.assertNotContains(resp, 'aria-label="Filtrar por equipe"')

    def test_oferecer_e_desistir(self):
        from escala.models import Rendimento
        self.preencher_recepcao()
        # Volta para a mesma página e filtros (e só com os parâmetros da lista).
        resp = self.client.post(reverse('oferecer_para_vaga', args=[self.vaga_louvor.pk]),
                                {'voltar': f'equipe={self.louvor.pk}&page=2&outro=x'})
        self.assertRedirects(resp, reverse('vagas_abertas') + f'?equipe={self.louvor.pk}&page=2',
                             fetch_redirect_response=False)
        self.assertTrue(Rendimento.objects.filter(escala=self.vaga_louvor, candidato=self.user).exists())
        self.assertNotContains(self.client.get('/'), 'Sua equipe precisa de ajuda')  # já se ofereceu
        self.client.post(reverse('desistir_da_vaga', args=[self.vaga_louvor.pk]))
        self.assertFalse(Rendimento.objects.exists())

    def test_filtro_de_data_so_com_periodos_que_separam_a_lista(self):
        inicio = timezone.now() + timedelta(days=40)  # nunca nesta semana nem na próxima
        distante = Evento.objects.create(nome='Culto distante', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        vaga_distante = Escala.objects.create(funcao=self.vaga_louvor.funcao, evento=distante)
        resp = self.client.get(reverse('vagas_abertas'))
        semanas = [valor for valor, _ in resp.context['periodos'] if valor in ('semana', 'proxima-semana')]
        self.assertEqual(len(semanas), 1)  # o culto de daqui a 5 dias cai numa das duas
        resp = self.client.get(reverse('vagas_abertas'), {'quando': semanas[0]})
        self.assertEqual({v.pk for v in resp.context['page_obj']}, {self.vaga_recepcao.pk, self.vaga_louvor.pk})
        self.assertContains(resp, 'Mostrando 2 de 3 vagas')
        self.assertContains(resp, 'Limpar filtros')
        # Período inexistente é ignorado.
        resp = self.client.get(reverse('vagas_abertas'), {'quando': 'ontem'})
        self.assertIn(vaga_distante.pk, {v.pk for v in resp.context['page_obj']})

    def test_paginacao(self):
        from escala import vagas_views
        funcao = self.vaga_louvor.funcao
        for dias in range(6, 6 + vagas_views.POR_PAGINA):
            inicio = timezone.now() + timedelta(days=dias)
            Escala.objects.create(funcao=funcao, evento=Evento.objects.create(
                nome=f'Culto {dias}', data_inicio=inicio, data_fim=inicio + timedelta(hours=2)))
        resp = self.client.get(reverse('vagas_abertas'))
        self.assertEqual(len(resp.context['page_obj']), vagas_views.POR_PAGINA)
        self.assertContains(resp, 'Página 1 de 2')
        resp = self.client.get(reverse('vagas_abertas'), {'page': 2})
        self.assertEqual(len(resp.context['page_obj']), 2)
