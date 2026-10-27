"""Painel do líder no app, push para o líder, Recusar no site e link de agenda (.ics)."""
from datetime import datetime, timedelta

from django.core import mail
from django.urls import reverse
from django.utils import timezone

from api.models import Device
from disponivel.models import Disponivel
from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala.models import Desistencia, Escala, Funcao, Rendimento, SolicitacaoTroca
from evento.models import Evento

from .test_conta import criar_usuario
from .test_push import OUTRO_TOKEN, PushTestCase

TOKEN_LIDER = 'ExponentPushToken[cccccccccccccccccccccc]'


class LiderancaTestCase(PushTestCase):
    """Base: `self.user` (com app) escalado na Recepção, `self.lider` (com app) liderando a Recepção."""

    def setUp(self):
        super().setUp()
        MembrosEquipe.objects.create(usuario=self.user, equipe=self.equipe, aprovado=True)
        self.lider = criar_usuario(username='lider', cpf='39053344705', first_name='Ana', last_name='Líder')
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)
        Device.objects.create(usuario=self.lider, expo_token=TOKEN_LIDER, plataforma='android')
        self.user.first_name, self.user.last_name = 'Maria', 'Silva'
        self.user.save()
        self.post.reset_mock()

    def enviadas_para(self, token):
        return [(m['title'], m['body']) for m in self.mensagens() if m['to'] == token]

    def como(self, usuario):
        self.autenticar(usuario)
        return self.client

    def acao(self, rota, pk, acao, usuario=None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.como(usuario or self.lider).post(f'/api/v1/lider/{rota}/{pk}/{acao}/')


class PushParaOLiderTests(LiderancaTestCase):
    def test_impedimento_pelo_app_avisa_o_lider(self):
        self.autenticar(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f'/api/v1/escalas/{self.escala.pk}/impedimento/', {'motivo': 'Viagem'}, format='json')
        ((titulo, corpo),) = self.enviadas_para(TOKEN_LIDER)
        self.assertEqual(titulo, 'Impedimento na escala')
        self.assertTrue(corpo.startswith('Maria Silva · '))
        self.assertTrue(corpo.endswith(' · Porta'))
        (msg,) = [m for m in self.mensagens() if m['to'] == TOKEN_LIDER]
        self.assertEqual(msg['data']['tipo'], 'pendencia_lider')  # o app abre a aba Liderança

    def test_troca_e_candidatura_avisam_o_lider(self):
        with self.captureOnCommitCallbacks(execute=True):
            SolicitacaoTroca.objects.create(
                escala_origem=self.escala, solicitante=self.user, tipo_solicitacao='desistencia',
                data_solicitacao=timezone.now())
            novato = criar_usuario(username='joao', cpf='11144477735', first_name='João')
            MembrosEquipe.objects.create(usuario=novato, equipe=self.equipe)
        self.assertEqual(
            [titulo for titulo, _ in self.enviadas_para(TOKEN_LIDER)], ['Pedido de troca', 'Nova candidatura'])
        self.assertIn(('Nova candidatura', 'João quer entrar na equipe Recepção'), self.enviadas_para(TOKEN_LIDER))

    def test_lider_que_pede_nao_avisa_a_si_mesmo(self):
        escala = Escala.objects.create(usuario=self.lider, funcao=self.funcao, evento=self.evento)
        self.post.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            Desistencia.objects.create(escala=escala, usuario=self.lider, motivo='Viagem')
        self.assertEqual(self.enviadas_para(TOKEN_LIDER), [])

    def test_membro_incluido_ja_aprovado_nao_avisa(self):
        with self.captureOnCommitCallbacks(execute=True):
            MembrosEquipe.objects.create(
                usuario=criar_usuario(username='joao', cpf='11144477735'), equipe=self.equipe, aprovado=True)
        self.assertEqual(self.enviadas_para(TOKEN_LIDER), [])


class PendenciasTests(LiderancaTestCase):
    def setUp(self):
        super().setUp()
        self.desistencia = Desistencia.objects.create(escala=self.escala, usuario=self.user, motivo='Viagem')
        self.novato = criar_usuario(username='joao', cpf='11144477735')
        self.candidatura = MembrosEquipe.objects.create(usuario=self.novato, equipe=self.equipe)
        self.post.reset_mock()

    def test_lista_pendencias_e_contagem_na_home(self):
        resp = self.como(self.lider).get('/api/v1/lider/pendencias/')
        self.assertEqual(resp.status_code, 200)
        (impedimento,) = resp.data['impedimentos']
        self.assertEqual((impedimento['motivo'], impedimento['pessoa']['nome']), ('Viagem', 'Maria Silva'))
        self.assertEqual(impedimento['escala']['funcao'], 'Porta')
        self.assertEqual(resp.data['trocas'], [])
        self.assertEqual(resp.data['candidaturas'][0]['equipe'], 'Recepção')
        self.assertEqual(self.client.get('/api/v1/home/').data['pendencias_lider'], 2)
        self.assertTrue(self.client.get('/api/v1/me/').data['lider'])

    def test_recusar_impedimento_mantem_escalado_e_avisa(self):
        resp = self.acao('impedimentos', self.desistencia.pk, 'recusar')
        self.assertEqual(resp.status_code, 204)
        self.escala.refresh_from_db()
        self.assertEqual(self.escala.usuario, self.user)
        self.assertFalse(Desistencia.objects.exists())
        ((titulo, corpo),) = self.enviadas_para(self.device.expo_token)
        self.assertEqual(titulo, 'Você continua escalado')
        self.assertIn('A liderança não aprovou o pedido', corpo)

    def test_aprovar_impedimento_libera_a_vaga(self):
        resp = self.acao('impedimentos', self.desistencia.pk, 'aprovar')
        self.assertEqual(resp.data, {'vaga_id': self.escala.pk})
        self.escala.refresh_from_db()
        self.assertIsNone(self.escala.usuario)
        self.assertEqual([t for t, _ in self.enviadas_para(self.device.expo_token)], ['Impedimento aceito'])
        # Já resolvido: não aparece mais e não pode ser recusado.
        self.assertEqual(self.acao('impedimentos', self.desistencia.pk, 'recusar').status_code, 404)

    def test_trocas(self):
        troca = SolicitacaoTroca.objects.create(
            escala_origem=self.escala, solicitante=self.user, tipo_solicitacao='desistencia',
            data_solicitacao=timezone.now())
        self.post.reset_mock()
        self.assertEqual(self.acao('trocas', troca.pk, 'recusar').status_code, 204)
        self.escala.refresh_from_db()
        self.assertEqual(self.escala.usuario, self.user)
        self.assertEqual([t for t, _ in self.enviadas_para(self.device.expo_token)], ['Você continua escalado'])

        troca = SolicitacaoTroca.objects.create(
            escala_origem=self.escala, solicitante=self.user, tipo_solicitacao='desistencia',
            data_solicitacao=timezone.now())
        self.assertEqual(self.acao('trocas', troca.pk, 'aprovar').data, {'vaga_id': self.escala.pk})
        troca.refresh_from_db()
        self.assertEqual((troca.aprovada, troca.lider_aprovador), (True, self.lider))

    def test_candidaturas(self):
        Device.objects.create(usuario=self.novato, expo_token=OUTRO_TOKEN, plataforma='ios')
        self.assertEqual(self.acao('candidaturas', self.candidatura.pk, 'aprovar').status_code, 204)
        self.candidatura.refresh_from_db()
        self.assertTrue(self.candidatura.aprovado)
        self.assertEqual(
            self.enviadas_para(OUTRO_TOKEN), [('Boas-vindas à equipe! 🙌', 'Agora você faz parte da equipe Recepção')])

        outra = MembrosEquipe.objects.create(
            usuario=criar_usuario(username='pedro', cpf='12345678909'), equipe=self.equipe)
        self.assertEqual(self.acao('candidaturas', outra.pk, 'recusar').status_code, 204)
        self.assertFalse(MembrosEquipe.objects.filter(pk=outra.pk).exists())

    def test_lider_de_outra_equipe_e_voluntario_nao_acessam(self):
        outra_equipe = Equipe.objects.create(nome='Louvor')
        lider_de_fora = criar_usuario(username='pedro', cpf='12345678909')
        Lideranca.objects.create(usuario=lider_de_fora, equipe=outra_equipe)

        resp = self.como(lider_de_fora).get('/api/v1/lider/pendencias/')
        self.assertEqual(resp.data, {'impedimentos': [], 'trocas': [], 'ofertas': [], 'candidaturas': []})
        for rota, pk in (('impedimentos', self.desistencia.pk), ('candidaturas', self.candidatura.pk)):
            for acao in ('aprovar', 'recusar'):
                self.assertEqual(self.acao(rota, pk, acao, usuario=lider_de_fora).status_code, 404)

        self.como(self.user)
        for url in ('/api/v1/lider/pendencias/', '/api/v1/lider/vagas/', f'/api/v1/lider/vagas/{self.escala.pk}/'):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.acao('impedimentos', self.desistencia.pk, 'aprovar', usuario=self.user).status_code, 403)
        self.assertFalse(self.client.get('/api/v1/me/').data['lider'])
        self.assertEqual(self.client.get('/api/v1/home/').data['pendencias_lider'], 0)
        self.escala.refresh_from_db()
        self.assertEqual(self.escala.usuario, self.user)


class RecusarPeloSiteTests(LiderancaTestCase):
    def test_botao_recusar_impedimento_e_troca(self):
        desistencia = Desistencia.objects.create(escala=self.escala, usuario=self.user, motivo='Viagem')
        self.client.force_login(self.lider)
        resp = self.client.get(reverse('detalhes_desistencia_escala', args=[self.escala.pk]))
        self.assertContains(resp, reverse('recusar_desistencia', args=[desistencia.pk]))
        self.post.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('recusar_desistencia', args=[desistencia.pk]))
        self.assertFalse(Desistencia.objects.exists())
        self.assertEqual([t for t, _ in self.enviadas_para(self.device.expo_token)], ['Você continua escalado'])

        troca = SolicitacaoTroca.objects.create(
            escala_origem=self.escala, solicitante=self.user, tipo_solicitacao='desistencia',
            data_solicitacao=timezone.now())
        resp = self.client.get(reverse('detalhes_solicitacao_troca', args=[troca.pk]))
        self.assertContains(resp, reverse('recusar_solicitacao_troca', args=[troca.pk]))
        self.client.post(reverse('recusar_solicitacao_troca', args=[troca.pk]))
        self.assertFalse(SolicitacaoTroca.objects.exists())
        self.escala.refresh_from_db()
        self.assertEqual(self.escala.usuario, self.user)

    def test_voluntario_nao_recusa(self):
        desistencia = Desistencia.objects.create(escala=self.escala, usuario=self.user, motivo='Viagem')
        self.client.force_login(self.user)
        self.client.post(reverse('recusar_desistencia', args=[desistencia.pk]))
        self.assertTrue(Desistencia.objects.exists())


class VagasTests(LiderancaTestCase):
    def setUp(self):
        super().setUp()
        self.vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        self.outro_evento = Evento.objects.create(
            nome='Culto de Quarta', data_inicio=self.evento.data_inicio + timedelta(days=1),
            data_fim=self.evento.data_fim + timedelta(days=1))
        self.vaga_quarta = Escala.objects.create(funcao=self.funcao, evento=self.outro_evento)
        self.disponivel = criar_usuario(username='joao', cpf='11144477735', first_name='João')
        self.sem_disp = criar_usuario(username='pedro', cpf='12345678909', first_name='Pedro')
        for pessoa in (self.disponivel, self.sem_disp):
            MembrosEquipe.objects.create(usuario=pessoa, equipe=self.equipe, aprovado=True)
        Disponivel.objects.create(
            usuario=self.disponivel, evento=self.evento,
            data_inicio=self.evento.data_inicio, data_fim=self.evento.data_fim)
        self.post.reset_mock()

    def test_lista_e_detalhe_com_disponiveis_primeiro(self):
        resp = self.como(self.lider).get('/api/v1/lider/vagas/')
        self.assertEqual([(v['id'], v['disponiveis']) for v in resp.data], [(self.vaga.pk, 1), (self.vaga_quarta.pk, 0)])

        resp = self.client.get(f'/api/v1/lider/vagas/{self.vaga.pk}/')
        candidatos = [(c['nome'], c['disponivel']) for c in resp.data['candidatos']]
        # Maria já está escalada neste evento e fica de fora.
        self.assertEqual(candidatos, [('João', True), ('Pedro', False)])
        self.assertEqual(resp.data['vaga']['disponiveis'], 1)

    def test_escalar_avisa_a_pessoa(self):
        Device.objects.create(usuario=self.disponivel, expo_token=OUTRO_TOKEN, plataforma='ios')
        self.autenticar(self.lider)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                f'/api/v1/lider/vagas/{self.vaga.pk}/escalar/', {'usuario_id': self.disponivel.pk}, format='json')
        self.assertEqual(resp.status_code, 204)
        self.vaga.refresh_from_db()
        self.assertEqual(self.vaga.usuario, self.disponivel)
        self.assertEqual([t for t, _ in self.enviadas_para(OUTRO_TOKEN)], ['Você foi escalado 🙌'])
        # A vaga saiu da lista e não aceita outra pessoa.
        self.assertEqual(self.client.post(
            f'/api/v1/lider/vagas/{self.vaga.pk}/escalar/', {'usuario_id': self.sem_disp.pk}, format='json',
        ).status_code, 404)

    def test_nao_escala_quem_nao_e_membro_nem_quem_ja_serve_no_evento(self):
        self.autenticar(self.lider)
        de_fora = criar_usuario(username='ze', cpf='98765432100')
        resp = self.client.post(f'/api/v1/lider/vagas/{self.vaga.pk}/escalar/', {'usuario_id': de_fora.pk}, format='json')
        self.assertEqual((resp.status_code, resp.data['code']), (400, 'nao_membro'))
        resp = self.client.post(f'/api/v1/lider/vagas/{self.vaga.pk}/escalar/', {'usuario_id': self.user.pk}, format='json')
        self.assertEqual((resp.status_code, resp.data['code']), (400, 'ja_escalado'))
        self.vaga.refresh_from_db()
        self.assertIsNone(self.vaga.usuario)


class AgendaTests(PushTestCase):
    def links(self):
        self.autenticar(self.user)
        return self.client.get('/api/v1/me/agenda/').data

    def baixar(self, url, **params):
        self.client.credentials()  # o link funciona sem login
        return self.client.get(url.replace('https://connect.pibvp.org.br', '').replace('http://testserver', ''), params)

    def test_links_e_arquivo(self):
        links = self.links()
        self.assertTrue(links['webcal'].startswith('webcal://'))
        resp = self.baixar(links['https'])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/calendar; charset=utf-8')
        self.assertIn(f'UID:escala-{self.escala.pk}@', resp.content.decode())

    def test_so_uma_escala_e_escala_de_outro(self):
        links = self.links()
        outra = Escala.objects.create(usuario=self.user, funcao=self.funcao, evento=self.evento)
        resp = self.baixar(links['https'], escala=self.escala.pk)
        conteudo = resp.content.decode()
        self.assertIn(f'UID:escala-{self.escala.pk}@', conteudo)
        self.assertNotIn(f'UID:escala-{outra.pk}@', conteudo)

        alheia = Escala.objects.create(
            usuario=criar_usuario(username='joao', cpf='11144477735'), funcao=self.funcao, evento=self.evento)
        self.assertEqual(self.baixar(links['https'], escala=alheia.pk).status_code, 404)

    def test_token_adulterado_ou_senha_trocada(self):
        links = self.links()
        self.assertEqual(self.baixar(links['https'].replace('.ics', 'x.ics')).status_code, 404)
        self.user.set_password('outra-senha-forte-456')
        self.user.save()
        self.assertEqual(self.baixar(links['https']).status_code, 404)


class OfertaParaVagaTests(LiderancaTestCase):
    """Voluntário se oferece para vaga da própria equipe; o líder aprova ou recusa."""

    def setUp(self):
        super().setUp()
        inicio = self.evento.data_inicio + timedelta(days=1)
        self.outro_culto = Evento.objects.create(nome='Culto de Quarta', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        self.vaga = Escala.objects.create(funcao=self.funcao, evento=self.outro_culto)
        Escala.objects.create(funcao=self.funcao, evento=self.evento)  # mesmo evento em que Maria já serve: fora
        Escala.objects.create(funcao=Funcao.objects.create(nome='Vocal', equipe=Equipe.objects.create(nome='Louvor')),
                              evento=self.outro_culto)  # equipe da qual Maria não faz parte: fora
        self.post.reset_mock()

    def oferecer(self, metodo='post'):
        self.autenticar(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            return getattr(self.client, metodo)(f'/api/v1/vagas/{self.vaga.pk}/oferta/')

    def test_lista_so_vagas_da_equipe_e_avisa_o_lider(self):
        self.autenticar(self.user)
        self.assertEqual([v['id'] for v in self.client.get('/api/v1/vagas/').data], [self.vaga.pk])
        self.assertEqual(self.client.get('/api/v1/home/').data['vagas_abertas'], 1)

        resp = self.oferecer()
        self.assertTrue(resp.data['me_ofereci'])
        ((titulo, corpo),) = self.enviadas_para(TOKEN_LIDER)
        self.assertEqual(titulo, 'Voluntário para a vaga')
        self.assertTrue(corpo.startswith('Maria Silva · '))
        self.assertEqual(self.client.get('/api/v1/home/').data['vagas_abertas'], 0)
        self.assertEqual(self.como(self.lider).get('/api/v1/home/').data['pendencias_lider'], 1)

        self.assertFalse(self.oferecer('delete').data['me_ofereci'])
        self.assertFalse(Rendimento.objects.exists())

    def test_vaga_com_alguem_disponivel_continua_na_lista(self):
        joao = criar_usuario(username='joao', cpf='11144477735')
        MembrosEquipe.objects.create(usuario=joao, equipe=self.equipe, aprovado=True)
        Disponivel.objects.create(usuario=joao, evento=self.outro_culto,
                                  data_inicio=self.outro_culto.data_inicio, data_fim=self.outro_culto.data_fim)
        self.autenticar(self.user)
        self.assertEqual([v['id'] for v in self.client.get('/api/v1/vagas/').data], [self.vaga.pk])
        self.assertEqual(self.client.get('/api/v1/home/').data['vagas_abertas'], 1)

        # Só some quando alguém é escalado.
        self.vaga.usuario = joao
        self.vaga.save()
        self.assertEqual(self.client.get('/api/v1/vagas/').data, [])
        self.assertEqual(self.client.get('/api/v1/home/').data['vagas_abertas'], 0)

    def ofertas_de(self, *nomes, vaga=None):
        """Outras pessoas da equipe se oferecem (direto no banco, como pelo site)."""
        cpfs = {'joao': '11144477735', 'pedro': '12345678909'}
        with self.captureOnCommitCallbacks(execute=True):
            for nome in nomes:
                pessoa = criar_usuario(username=nome, cpf=cpfs[nome])
                MembrosEquipe.objects.create(usuario=pessoa, equipe=self.equipe, aprovado=True)
                Rendimento.objects.create(escala=vaga or self.vaga, candidato=pessoa)

    def aviso_de_ofertas(self):
        from api.models import Aviso
        return Aviso.objects.get(usuario=self.lider, purpose='oferta_lider')

    def test_varias_ofertas_no_mesmo_culto_tocam_o_celular_do_lider_uma_vez(self):
        self.oferecer()
        self.ofertas_de('joao', 'pedro')
        self.assertEqual([t for t, _ in self.enviadas_para(TOKEN_LIDER)], ['Voluntário para a vaga'])
        aviso = self.aviso_de_ofertas()  # um aviso só na caixa, atualizado e de novo não lido
        self.assertEqual((aviso.titulo, aviso.lido_em), ('3 pessoas querem servir', None))
        self.assertTrue(aviso.corpo.startswith('Culto de Quarta · '))

    def test_aviso_de_oferta_abre_o_culto_com_quem_se_ofereceu(self):
        self.oferecer()
        self.ofertas_de('joao')
        # Push e caixa de avisos levam o culto, para o app abrir a tela dele.
        (push,) = [m for m in self.mensagens() if m['to'] == TOKEN_LIDER]
        self.assertEqual(push['data'], {'tipo': 'oferta_lider', 'escala_id': self.vaga.pk, 'evento_id': self.outro_culto.pk})
        (aviso,) = [a for a in self.como(self.lider).get('/api/v1/avisos/').data['avisos'] if a['tipo'] == 'oferta_lider']
        self.assertEqual(aviso['evento_id'], self.outro_culto.pk)

        escalas = self.client.get(f'/api/v1/lider/cultos/{self.outro_culto.pk}/').data['escalas']
        (vaga,) = [e for e in escalas if e['id'] == self.vaga.pk]
        self.assertEqual([p['nome'] for p in vaga['ofertas']], ['Maria Silva', 'joao'])
        self.assertEqual(vaga['disponiveis'], 0)

    def test_outro_culto_ou_depois_de_12h_avisa_de_novo(self):
        from api.models import Aviso
        self.oferecer()
        outro = Escala.objects.create(funcao=self.funcao, evento=Evento.objects.create(
            nome='Culto de Sexta', data_inicio=self.outro_culto.data_inicio + timedelta(days=2),
            data_fim=self.outro_culto.data_fim + timedelta(days=2)))
        self.ofertas_de('joao', vaga=outro)
        self.assertEqual(len(self.enviadas_para(TOKEN_LIDER)), 2)

        Aviso.objects.filter(usuario=self.lider).update(criado_em=timezone.now() - timedelta(hours=13))
        self.ofertas_de('pedro')
        self.assertEqual(len(self.enviadas_para(TOKEN_LIDER)), 3)

    def test_lider_aprova_e_os_outros_sao_avisados(self):
        self.oferecer()
        joao = criar_usuario(username='joao', cpf='11144477735')
        MembrosEquipe.objects.create(usuario=joao, equipe=self.equipe, aprovado=True)
        Device.objects.create(usuario=joao, expo_token=OUTRO_TOKEN, plataforma='ios')
        Rendimento.objects.create(escala=self.vaga, candidato=joao)

        resp = self.como(self.lider).get('/api/v1/lider/pendencias/')
        self.assertEqual([o['pessoa']['nome'] for o in resp.data['ofertas']], ['Maria Silva', 'joao'])
        candidatos = self.client.get(f'/api/v1/lider/vagas/{self.vaga.pk}/').data['candidatos']
        self.assertEqual([c['se_ofereceu'] for c in candidatos], [True, True])

        oferta = Rendimento.objects.get(candidato=self.user)
        self.post.reset_mock()
        self.assertEqual(self.acao('ofertas', oferta.pk, 'aprovar').status_code, 204)
        self.vaga.refresh_from_db()
        self.assertEqual(self.vaga.usuario, self.user)
        self.assertEqual([t for t, _ in self.enviadas_para(self.device.expo_token)], ['Você foi escalado 🙌'])
        self.assertEqual([t for t, _ in self.enviadas_para(OUTRO_TOKEN)], ['Obrigado por se oferecer'])
        self.assertEqual(list(Rendimento.objects.values_list('candidato', 'aprovada')), [(self.user.pk, True)])
        self.assertEqual(self.client.get('/api/v1/lider/pendencias/').data['ofertas'], [])

    def test_lider_recusa(self):
        self.oferecer()
        oferta = Rendimento.objects.get()
        self.post.reset_mock()
        self.assertEqual(self.acao('ofertas', oferta.pk, 'recusar').status_code, 204)
        self.assertFalse(Rendimento.objects.exists())
        self.vaga.refresh_from_db()
        self.assertIsNone(self.vaga.usuario)
        ((titulo, corpo),) = self.enviadas_para(self.device.expo_token)
        self.assertEqual(titulo, 'Obrigado por se oferecer')
        self.assertIn('não ficou com você', corpo)

    def test_nao_se_oferece_para_vaga_de_outra_equipe_nem_ocupada(self):
        self.autenticar(self.user)
        alheia = Escala.objects.exclude(funcao=self.funcao).get()
        resp = self.client.post(f'/api/v1/vagas/{alheia.pk}/oferta/')
        self.assertEqual((resp.status_code, resp.data['code']), (400, 'vaga_indisponivel'))
        self.vaga.usuario = criar_usuario(username='joao', cpf='11144477735')
        self.vaga.save()
        resp = self.client.post(f'/api/v1/vagas/{self.vaga.pk}/oferta/')
        self.assertEqual(resp.data['code'], 'vaga_indisponivel')


class CultosDoLiderTests(LiderancaTestCase):
    def setUp(self):
        super().setUp()
        self.joao = criar_usuario(username='joao', cpf='11144477735', first_name='João')
        Device.objects.create(usuario=self.joao, expo_token=OUTRO_TOKEN, plataforma='ios')
        Escala.objects.create(usuario=self.joao, funcao=self.funcao, evento=self.evento, confirmada=True)
        Escala.objects.create(funcao=self.funcao, evento=self.evento)  # vaga
        # Outra equipe no mesmo culto: não aparece nem recebe pedido.
        louvor = Funcao.objects.create(nome='Vocal', equipe=Equipe.objects.create(nome='Louvor'))
        self.pedro = criar_usuario(username='pedro', cpf='12345678909')
        Device.objects.create(usuario=self.pedro, expo_token=TOKEN_LIDER.replace('c', 'd'), plataforma='ios')
        Escala.objects.create(usuario=self.pedro, funcao=louvor, evento=self.evento)
        self.post.reset_mock()

    def test_lista_detalhe_e_pedido_de_confirmacao(self):
        (culto,) = self.como(self.lider).get('/api/v1/lider/cultos/').data
        self.assertEqual((culto['id'], culto['total'], culto['confirmadas'], culto['pendentes'], culto['vagas']),
                         (self.evento.pk, 3, 1, 1, 1))
        self.assertEqual(culto['por_equipe'], [{'equipe_id': self.equipe.pk, 'equipe': self.equipe.nome,
                                                'total': 3, 'vagas': 1, 'confirmadas': 1, 'pendentes': 1}])

        resp = self.client.get(f'/api/v1/lider/cultos/{self.evento.pk}/')
        self.assertEqual(
            [(e['pessoa'] and e['pessoa']['nome'], e['confirmada']) for e in resp.data['escalas']],
            [('Maria Silva', False), ('João', True), (None, False)])

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(f'/api/v1/lider/cultos/{self.evento.pk}/pedir-confirmacao/')
        self.assertEqual(resp.data, {'pendentes': 1})
        # Só Maria (não confirmou, equipe do líder): nem João (confirmado) nem Pedro (outra equipe).
        self.assertEqual([m['to'] for m in self.mensagens()], [self.device.expo_token])
        self.assertEqual(self.mensagens()[0]['title'], 'Confirma sua escala?')

    def test_lider_de_duas_equipes_ve_contagem_por_equipe(self):
        Lideranca.objects.create(usuario=self.lider, equipe=Equipe.objects.get(nome='Louvor'))
        (culto,) = self.como(self.lider).get('/api/v1/lider/cultos/').data
        self.assertEqual((culto['total'], culto['pendentes']), (4, 2))
        self.assertEqual([(e['equipe'], e['total'], e['pendentes']) for e in culto['por_equipe']],
                         [('Louvor', 1, 1), (self.equipe.nome, 3, 1)])

    def test_lider_de_outra_equipe_nao_ve(self):
        lider_de_fora = criar_usuario(username='ze', cpf='98765432100')
        Lideranca.objects.create(usuario=lider_de_fora, equipe=Equipe.objects.create(nome='Mídia'))
        self.assertEqual(self.como(lider_de_fora).get('/api/v1/lider/cultos/').data, [])
        self.assertEqual(self.client.get(f'/api/v1/lider/cultos/{self.evento.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/v1/lider/cultos/{self.evento.pk}/pedir-confirmacao/').status_code, 404)
        self.post.assert_not_called()


class PedirDisponibilidadePeloAppTests(LiderancaTestCase):
    def setUp(self):
        super().setUp()
        self.joao = criar_usuario(username='joao', cpf='11144477735', first_name='João')
        MembrosEquipe.objects.create(usuario=self.joao, equipe=self.equipe, aprovado=True)
        hoje = timezone.localdate()
        self.ano, self.mes = (hoje.year + 1, 1) if hoje.month == 12 else (hoje.year, hoje.month + 1)
        inicio = timezone.make_aware(datetime(self.ano, self.mes, 15, 19, 0))
        culto = Evento.objects.create(nome='Culto do mês', data_inicio=inicio, data_fim=inicio + timedelta(hours=2))
        Disponivel.objects.create(usuario=self.joao, evento=culto, data_inicio=culto.data_inicio, data_fim=culto.data_fim)
        self.post.reset_mock()

    def test_mostra_quem_falta_e_pede_so_pelo_app(self):
        resp = self.como(self.lider).get('/api/v1/lider/disponibilidade/')
        self.assertEqual((resp.data['equipe_id'], resp.data['ano'], resp.data['mes']), (self.equipe.pk, self.ano, self.mes))
        self.assertEqual([p['nome'] for p in resp.data['faltantes']], ['Maria Silva'])
        self.assertEqual(resp.data['membros'], 2)

        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post('/api/v1/lider/disponibilidade/pedir/', {
                'equipe_id': self.equipe.pk, 'ano': self.ano, 'mes': self.mes, 'canal': 'app'}, format='json')
        self.assertEqual(resp.data, {'faltantes': 1})
        self.assertEqual([(m['to'], m['title']) for m in self.mensagens()],
                         [(self.device.expo_token, 'Quando você pode servir?')])
        self.assertEqual(mail.outbox, [])

    def test_equipe_de_outro_lider_e_voluntario(self):
        outra = Equipe.objects.create(nome='Louvor')
        resp = self.como(self.lider).post('/api/v1/lider/disponibilidade/pedir/', {
            'equipe_id': outra.pk, 'ano': self.ano, 'mes': self.mes, 'canal': 'todos'}, format='json')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/lider/disponibilidade/?equipe={outra.pk}').status_code, 404)
        self.assertEqual(self.como(self.user).get('/api/v1/lider/disponibilidade/').status_code, 403)
        self.post.assert_not_called()
