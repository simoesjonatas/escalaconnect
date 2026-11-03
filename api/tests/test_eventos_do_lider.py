from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from equipe.models import Equipe, Lideranca
from escala.models import Escala, Funcao
from evento.models import Evento

from .test_conta import criar_usuario
from .test_lideranca import LiderancaTestCase


class FerramentasDoLiderTestCase(LiderancaTestCase):
    """Base: líder da Recepção (funções Porta e Café); a Mídia é de outra liderança."""

    def setUp(self):
        super().setUp()
        self.cafe = Funcao.objects.create(nome='Café', equipe=self.equipe)
        self.midia = Equipe.objects.create(nome='Mídia')
        self.camera = Funcao.objects.create(nome='Câmera', equipe=self.midia)
        self.autenticar(self.lider)


class CriarEventoTests(FerramentasDoLiderTestCase):
    def novo(self, **extra):
        inicio = timezone.now() + timedelta(days=10)
        dados = {'nome': 'Ensaio', 'equipe_id': self.equipe.pk, 'data_inicio': inicio.isoformat(),
                 'data_fim': (inicio + timedelta(hours=2)).isoformat(), 'funcao_ids': [self.funcao.pk, self.cafe.pk]}
        return self.client.post('/api/v1/lider/eventos/', {**dados, **extra}, format='json')

    def test_opcoes_trazem_so_as_equipes_do_lider(self):
        resp = self.client.get('/api/v1/lider/eventos/opcoes/')
        self.assertEqual([(e['nome'], [f['nome'] for f in e['funcoes']]) for e in resp.data['equipes']],
                         [('Recepção', ['Café', 'Porta'])])
        self.assertEqual(len(resp.data['meses']), 2)
        self.assertFalse(resp.data['admin'])

    def test_cria_evento_da_equipe_com_as_vagas(self):
        resp = self.novo()
        self.assertEqual(resp.status_code, 201)
        evento = Evento.objects.get(pk=resp.data['id'])
        self.assertEqual((evento.nome, evento.equipe), ('Ensaio', self.equipe))
        self.assertEqual(sorted(Escala.objects.filter(evento=evento, usuario__isnull=True)
                                .values_list('funcao__nome', flat=True)), ['Café', 'Porta'])

    def test_regras(self):
        self.assertEqual(self.novo(equipe_id=self.midia.pk).status_code, 404)  # equipe de outra liderança
        self.assertIn('funcao_ids', self.novo(funcao_ids=[self.camera.pk]).data['errors'])
        self.assertIn('equipe_id', self.novo(equipe_id=None).data['errors'])  # público só admin
        passado = timezone.now() - timedelta(days=1)
        self.assertIn('data_inicio', self.novo(data_inicio=passado.isoformat(),
                                               data_fim=(passado + timedelta(hours=1)).isoformat()).data['errors'])
        self.assertFalse(Evento.objects.filter(nome='Ensaio').exists())

    def test_voluntario_nao_acessa(self):
        self.autenticar(criar_usuario(username='joao', cpf='11144477735'))
        self.assertEqual(self.client.get('/api/v1/lider/eventos/opcoes/').status_code, 403)
        self.assertEqual(self.novo().status_code, 403)


class EventosEmMassaTests(FerramentasDoLiderTestCase):
    def test_gera_nos_dias_escolhidos_do_proximo_mes(self):
        proximo = self.client.get('/api/v1/lider/eventos/opcoes/').data['meses'][1]['valor']
        resp = self.client.post('/api/v1/lider/eventos/em-massa/', {
            'nome': 'Reunião', 'equipe_id': self.equipe.pk, 'meses': [proximo], 'dias_da_semana': [6],
            'horario_inicio': '18:00', 'horario_fim': '19:00', 'funcao_ids': [self.cafe.pk],
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        eventos = Evento.objects.filter(nome='Reunião')
        self.assertEqual(resp.data['criados'], eventos.count())
        self.assertGreaterEqual(eventos.count(), 4)
        self.assertTrue(all(timezone.localtime(e.data_inicio).weekday() == 6 for e in eventos))
        self.assertEqual(Escala.objects.filter(evento__in=eventos, funcao=self.cafe).count(), eventos.count())

        # De novo: tudo já existe e é ignorado.
        resp = self.client.post('/api/v1/lider/eventos/em-massa/', {
            'nome': 'Reunião', 'equipe_id': self.equipe.pk, 'meses': [proximo], 'dias_da_semana': [6],
            'horario_inicio': '18:00', 'horario_fim': '19:00',
        }, format='json')
        self.assertEqual(resp.data['criados'], 0)

    def test_so_mes_atual_ou_proximo(self):
        resp = self.client.post('/api/v1/lider/eventos/em-massa/', {
            'nome': 'Reunião', 'equipe_id': self.equipe.pk, 'meses': ['2099-01'], 'dias_da_semana': [6],
            'horario_inicio': '18:00', 'horario_fim': '19:00',
        }, format='json')
        self.assertIn('meses', resp.data['errors'])


class AplicarFuncoesTests(FerramentasDoLiderTestCase):
    def test_adiciona_funcoes_ao_culto_publico_sem_duplicar(self):
        eventos = self.client.get('/api/v1/lider/eventos/').data
        (culto,) = [e for e in eventos if e['id'] == self.evento.pk]
        self.assertEqual(culto['funcao_ids'], [self.funcao.pk])  # já tem a Porta (escala de Maria)

        resp = self.client.post('/api/v1/lider/eventos/funcoes/', {
            'evento_ids': [self.evento.pk], 'funcao_ids': [self.funcao.pk, self.cafe.pk]}, format='json')
        self.assertEqual(resp.data, {'criadas': 1, 'existentes': 1})
        self.assertTrue(Escala.objects.filter(evento=self.evento, funcao=self.cafe, usuario__isnull=True).exists())

    def test_nao_mexe_em_evento_ou_funcao_de_outra_equipe(self):
        inicio = timezone.now() + timedelta(days=5)
        da_midia = Evento.objects.create(nome='Gravação', equipe=self.midia, data_inicio=inicio,
                                         data_fim=inicio + timedelta(hours=1))
        self.assertNotIn(da_midia.pk, [e['id'] for e in self.client.get('/api/v1/lider/eventos/').data])
        for evento, funcao in ((da_midia, self.cafe), (self.evento, self.camera)):
            resp = self.client.post('/api/v1/lider/eventos/funcoes/', {
                'evento_ids': [evento.pk], 'funcao_ids': [funcao.pk]}, format='json')
            self.assertEqual(resp.status_code, 400)
        self.assertFalse(Escala.objects.filter(funcao=self.camera).exists())


class PdfDaEscalaTests(FerramentasDoLiderTestCase):
    def link(self, equipe=None):
        local = timezone.localtime(self.evento.data_inicio)
        return self.client.post('/api/v1/lider/pdf/', {
            'equipe_id': (equipe or self.equipe).pk, 'ano': local.year, 'mes': local.month}, format='json')

    def test_link_abre_o_pdf_sem_login(self):
        url = self.link().data['url']
        self.client.logout()
        self.client.credentials()
        resp = self.client.get('/' + url.split('://', 1)[1].split('/', 1)[1])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp['Content-Disposition'].startswith('inline;'))
        self.assertTrue(resp.content.startswith(b'%PDF'))

    def test_equipe_de_outro_e_link_invalido_ou_de_quem_saiu_da_lideranca(self):
        self.assertEqual(self.link(self.midia).status_code, 404)
        caminho = '/' + self.link().data['url'].split('://', 1)[1].split('/', 1)[1]
        self.assertEqual(self.client.get(caminho[:-3] + 'xx/').status_code, 404)
        Lideranca.objects.filter(usuario=self.lider).delete()
        self.assertEqual(self.client.get(caminho).status_code, 404)

    def test_site_continua_exportando(self):
        self.client.force_login(self.lider)
        local = timezone.localtime(self.evento.data_inicio)
        resp = self.client.post(reverse('exportar_pdf', args=[self.equipe.pk]), {'mes': local.month})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp['Content-Disposition'].startswith('attachment;'))
