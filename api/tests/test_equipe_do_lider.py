from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala.models import Escala, Funcao

from .test_conta import criar_usuario
from .test_lideranca import LiderancaTestCase


class GestaoDaEquipeTestCase(LiderancaTestCase):
    """Base: líder Ana na Recepção (função Porta, com a escala de Maria); Mídia é de outra liderança."""

    def setUp(self):
        super().setUp()
        self.midia = Equipe.objects.create(nome='Mídia')
        self.autenticar(self.lider)
        self.url = f'/api/v1/lider/equipes/{self.equipe.pk}/'


class VerEquipeTests(GestaoDaEquipeTestCase):
    def test_mostra_funcoes_lideres_integrantes_e_pendentes(self):
        MembrosEquipe.objects.create(usuario=self.lider, equipe=self.equipe, aprovado=True)
        novato = criar_usuario(username='joao', cpf='11144477735', first_name='João')
        MembrosEquipe.objects.create(usuario=novato, equipe=self.equipe)
        resp = self.client.get(self.url)
        self.assertEqual(resp.data['nome'], 'Recepção')
        self.assertFalse(resp.data['pode_renomear'])
        self.assertEqual(resp.data['funcoes'], [{'id': self.funcao.pk, 'nome': 'Porta', 'escalas': 1}])
        self.assertEqual([(l['pessoa']['nome'], l['sou_eu']) for l in resp.data['lideres']], [('Ana Líder', True)])
        self.assertEqual([(i['pessoa']['nome'], i['lider'], i['escalas_futuras']) for i in resp.data['integrantes']],
                         [('Ana Líder', True, 0), ('Maria Silva', False, 1)])
        self.assertEqual([p['pessoa']['nome'] for p in resp.data['pendentes']], ['João'])

    def test_equipe_de_outro_e_voluntario_nao_acessam(self):
        self.assertEqual(self.client.get(f'/api/v1/lider/equipes/{self.midia.pk}/').status_code, 404)
        self.autenticar(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_so_admin_renomeia(self):
        self.assertEqual(self.client.patch(self.url, {'nome': 'Boas-vindas'}, format='json').status_code, 403)
        admin = criar_usuario(username='admin', cpf='98765432100', is_staff=True)
        self.autenticar(admin)
        self.assertEqual(self.client.patch(self.url, {'nome': 'Boas-vindas'}, format='json').data['nome'], 'Boas-vindas')
        self.equipe.refresh_from_db()
        self.assertEqual(self.equipe.nome, 'Boas-vindas')


class FuncoesTests(GestaoDaEquipeTestCase):
    def test_cria_renomeia_e_exclui_sem_escalas(self):
        resp = self.client.post(f'{self.url}funcoes/', {'nome': ' Café '}, format='json')
        self.assertEqual(resp.status_code, 201)
        cafe = Funcao.objects.get(pk=resp.data['id'])
        self.assertEqual((cafe.nome, cafe.equipe), ('Café', self.equipe))
        self.assertEqual(self.client.post(f'{self.url}funcoes/', {'nome': 'café'}, format='json').data['code'],
                         'funcao_repetida')

        self.assertEqual(self.client.patch(f'/api/v1/lider/funcoes/{cafe.pk}/', {'nome': 'Cafezinho'},
                                           format='json').data['nome'], 'Cafezinho')
        self.assertEqual(self.client.delete(f'/api/v1/lider/funcoes/{cafe.pk}/').status_code, 204)
        self.assertFalse(Funcao.objects.filter(pk=cafe.pk).exists())

    def test_nao_exclui_funcao_com_escalas(self):
        resp = self.client.delete(f'/api/v1/lider/funcoes/{self.funcao.pk}/')
        self.assertEqual((resp.status_code, resp.data['code']), (400, 'funcao_com_escalas'))
        self.assertTrue(Escala.objects.filter(funcao=self.funcao).exists())

    def test_nao_mexe_em_funcao_de_outra_equipe(self):
        camera = Funcao.objects.create(nome='Câmera', equipe=self.midia)
        self.assertEqual(self.client.delete(f'/api/v1/lider/funcoes/{camera.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/v1/lider/equipes/{self.midia.pk}/funcoes/', {'nome': 'X'},
                                          format='json').status_code, 404)


class LiderancasTests(GestaoDaEquipeTestCase):
    def test_remove_lider_mas_nao_o_ultimo(self):
        (minha,) = Lideranca.objects.filter(equipe=self.equipe)
        resp = self.client.delete(f'/api/v1/lider/liderancas/{minha.pk}/')
        self.assertEqual(resp.data['code'], 'ultimo_lider')
        outro = Lideranca.objects.create(equipe=self.equipe, usuario=criar_usuario(username='ze', cpf='98765432100'))
        self.assertEqual(self.client.delete(f'/api/v1/lider/liderancas/{outro.pk}/').status_code, 204)
        self.assertFalse(Lideranca.objects.filter(pk=outro.pk).exists())

    def test_nao_remove_lider_de_outra_equipe(self):
        de_fora = Lideranca.objects.create(equipe=self.midia, usuario=criar_usuario(username='ze', cpf='98765432100'))
        self.assertEqual(self.client.delete(f'/api/v1/lider/liderancas/{de_fora.pk}/').status_code, 404)


class IntegrantesTests(GestaoDaEquipeTestCase):
    def test_busca_adiciona_e_remove(self):
        joao = criar_usuario(username='joao', cpf='11144477735', first_name='João', last_name='Souza')
        resp = self.client.get(f'{self.url}integrantes/', {'q': 'joão sou'})
        self.assertEqual([p['nome'] for p in resp.data], ['João Souza'])
        self.assertEqual(self.client.get(f'{self.url}integrantes/', {'q': 'maria'}).data, [])  # já é integrante
        self.assertEqual(self.client.get(f'{self.url}integrantes/', {'q': 'j'}).data, [])  # busca curta

        resp = self.client.post(f'{self.url}integrantes/', {'usuario_id': joao.pk}, format='json')
        self.assertEqual(resp.status_code, 201)
        membro = MembrosEquipe.objects.get(equipe=self.equipe, usuario=joao)
        self.assertTrue(membro.aprovado)
        self.assertEqual(self.client.post(f'{self.url}integrantes/', {'usuario_id': joao.pk},
                                          format='json').data['code'], 'ja_membro')

        self.assertEqual(self.client.delete(f'/api/v1/lider/integrantes/{membro.pk}/').status_code, 204)
        self.assertFalse(MembrosEquipe.objects.filter(pk=membro.pk).exists())

    def test_adicionar_quem_tinha_candidatura_aprova_e_avisa(self):
        from api.models import Device
        joao = criar_usuario(username='joao', cpf='11144477735', first_name='João')
        Device.objects.create(usuario=joao, expo_token='ExponentPushToken[joao]', plataforma='ios')
        MembrosEquipe.objects.create(usuario=joao, equipe=self.equipe)
        self.post.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(f'{self.url}integrantes/', {'usuario_id': joao.pk}, format='json')
        self.assertTrue(MembrosEquipe.objects.get(usuario=joao, equipe=self.equipe).aprovado)
        self.assertEqual([t for t, _ in self.enviadas_para('ExponentPushToken[joao]')], ['Boas-vindas à equipe! 🙌'])

    def test_lider_sai_da_lideranca_antes(self):
        membro = MembrosEquipe.objects.create(usuario=self.lider, equipe=self.equipe, aprovado=True)
        resp = self.client.delete(f'/api/v1/lider/integrantes/{membro.pk}/')
        self.assertEqual(resp.data['code'], 'e_lider')

    def test_nao_remove_integrante_de_outra_equipe(self):
        de_fora = MembrosEquipe.objects.create(usuario=self.user, equipe=self.midia, aprovado=True)
        self.assertEqual(self.client.delete(f'/api/v1/lider/integrantes/{de_fora.pk}/').status_code, 404)
