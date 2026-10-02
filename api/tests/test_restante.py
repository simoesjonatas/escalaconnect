"""Calendário, disponibilidades/indisponibilidades, equipes, termo e senha."""
from datetime import timedelta

from django.utils import timezone
from knox.models import AuthToken

from disponivel.models import Disponivel
from equipe.models import Equipe, MembrosEquipe
from escala.models import Escala, Funcao
from evento.models import Evento
from ocupado.models import Ocupado

from .test_conta import ApiTestCase, criar_usuario


def em(dias, horas=0):
    return timezone.now() + timedelta(days=dias, hours=horas)


def criar_evento(nome, dias, equipe=None):
    return Evento.objects.create(nome=nome, data_inicio=em(dias), data_fim=em(dias, 2), equipe=equipe)


class BaseTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = criar_usuario()
        self.outro = criar_usuario(username='joao', cpf='11144477735')
        self.minha_equipe = Equipe.objects.create(nome='Recepção')
        self.outra_equipe = Equipe.objects.create(nome='Louvor')
        MembrosEquipe.objects.create(usuario=self.user, equipe=self.minha_equipe, aprovado=True)
        self.autenticar(self.user)


class EventosTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.publico = criar_evento('Culto', 2)
        self.da_equipe = criar_evento('Ensaio Recepção', 3, equipe=self.minha_equipe)
        self.alheio = criar_evento('Ensaio Louvor', 4, equipe=self.outra_equipe)
        funcao = Funcao.objects.create(nome='Porta', equipe=self.minha_equipe)
        Escala.objects.create(usuario=self.user, funcao=funcao, evento=self.publico)

    def nomes(self, query=''):
        resp = self.client.get(f'/api/v1/eventos/{query}')
        self.assertEqual(resp.status_code, 200)
        return [e['nome'] for e in resp.data]

    def test_so_eventos_visiveis_com_minhas_escalas(self):
        resp = self.client.get('/api/v1/eventos/')
        self.assertEqual([e['nome'] for e in resp.data], ['Culto', 'Ensaio Recepção'])
        culto, ensaio = resp.data
        self.assertTrue(culto['escalado'])
        self.assertFalse(culto['confirmada'])
        self.assertEqual(culto['funcoes'], ['Porta'])
        self.assertIsNone(culto['equipe'])
        self.assertFalse(ensaio['escalado'])
        self.assertEqual(ensaio['equipe'], 'Recepção')

    def test_filtros(self):
        self.assertEqual(self.nomes('?filtro=escalado'), ['Culto'])
        self.assertEqual(self.nomes('?equipe=publicos'), ['Culto'])
        self.assertEqual(self.nomes(f'?equipe={self.minha_equipe.pk}'), ['Ensaio Recepção'])
        # Filtrar por uma equipe alheia não expõe os eventos dela.
        self.assertEqual(self.nomes(f'?equipe={self.outra_equipe.pk}'), [])

    def test_janela_de_datas(self):
        criar_evento('Antigo', -60)
        criar_evento('Distante', 200)
        self.assertEqual(self.nomes(), ['Culto', 'Ensaio Recepção'])
        dia = timezone.localtime(self.da_equipe.data_inicio).date().isoformat()
        self.assertEqual(self.nomes(f'?inicio={dia}&fim={dia}'), ['Ensaio Recepção'])

    def test_parametros_invalidos(self):
        resp = self.client.get('/api/v1/eventos/?inicio=ontem')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'validacao')


class PeriodosTests(BaseTestCase):
    """As rotas de /indisponibilidades/ usam as mesmas views, com os models trocados."""

    def criar(self, rota, inicio, fim):
        return self.client.post(
            f'/api/v1/{rota}/', {'data_inicio': inicio.isoformat(), 'data_fim': fim.isoformat()}, format='json')

    def test_cria_lista_edita_e_exclui_disponibilidade(self):
        resp = self.criar('disponibilidades', em(2), em(2, 3))
        self.assertEqual(resp.status_code, 201)
        pk = resp.data['id']
        self.assertEqual(Disponivel.objects.get(pk=pk).usuario, self.user)

        Disponivel.objects.create(usuario=self.user, data_inicio=em(-5), data_fim=em(-5, 2))  # passada
        Disponivel.objects.create(usuario=self.outro, data_inicio=em(2), data_fim=em(2, 2))   # de outro
        self.assertEqual([p['id'] for p in self.client.get('/api/v1/disponibilidades/').data], [pk])

        novo_fim = em(2, 5)
        resp = self.client.patch(
            f'/api/v1/disponibilidades/{pk}/', {'data_fim': novo_fim.isoformat()}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Disponivel.objects.get(pk=pk).data_fim, novo_fim)

        self.assertEqual(self.client.delete(f'/api/v1/disponibilidades/{pk}/').status_code, 204)
        self.assertFalse(Disponivel.objects.filter(pk=pk).exists())

    def test_periodo_invertido(self):
        resp = self.criar('disponibilidades', em(2, 3), em(2))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'periodo_invalido')

    def test_conflito_entre_disponibilidade_e_indisponibilidade(self):
        self.assertEqual(self.criar('indisponibilidades', em(2), em(2, 3)).status_code, 201)
        resp = self.criar('disponibilidades', em(2, 1), em(2, 4))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'conflito')
        self.assertFalse(Disponivel.objects.exists())
        # Fora do período ocupado, pode.
        self.assertEqual(self.criar('disponibilidades', em(3), em(3, 2)).status_code, 201)
        # E o inverso também é barrado.
        resp = self.criar('indisponibilidades', em(3, 1), em(3, 3))
        self.assertEqual(resp.data['code'], 'conflito')

    def test_editar_para_um_periodo_em_conflito(self):
        Ocupado.objects.create(usuario=self.user, data_inicio=em(5), data_fim=em(5, 2))
        pk = self.criar('disponibilidades', em(2), em(2, 3)).data['id']
        resp = self.client.patch(
            f'/api/v1/disponibilidades/{pk}/',
            {'data_inicio': em(5).isoformat(), 'data_fim': em(5, 1).isoformat()}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'conflito')

    def test_registro_de_outro_usuario_e_404(self):
        for rota, modelo in (('disponibilidades', Disponivel), ('indisponibilidades', Ocupado)):
            alheio = modelo.objects.create(usuario=self.outro, data_inicio=em(2), data_fim=em(2, 2))
            url = f'/api/v1/{rota}/{alheio.pk}/'
            self.assertEqual(self.client.patch(url, {'data_fim': em(3).isoformat()}, format='json').status_code, 404)
            self.assertEqual(self.client.delete(url).status_code, 404)
            self.assertTrue(modelo.objects.filter(pk=alheio.pk).exists())

    def test_por_evento_respeita_visibilidade_e_nao_duplica(self):
        publico = criar_evento('Culto', 2)
        da_equipe = criar_evento('Ensaio Recepção', 3, equipe=self.minha_equipe)
        alheio = criar_evento('Ensaio Louvor', 4, equipe=self.outra_equipe)
        criar_evento('Distante', 90)  # fora da janela de 60 dias

        for rota, modelo in (('disponibilidades', Disponivel), ('indisponibilidades', Ocupado)):
            elegiveis = self.client.get(f'/api/v1/{rota}/eventos/').data
            self.assertEqual([e['nome'] for e in elegiveis], ['Culto', 'Ensaio Recepção'])

        ids = [publico.pk, da_equipe.pk, alheio.pk]
        resp = self.client.post('/api/v1/disponibilidades/por-evento/', {'evento_ids': ids}, format='json')
        self.assertEqual(resp.data, {'criados': 2})
        self.assertFalse(Disponivel.objects.filter(evento=alheio).exists())
        registro = Disponivel.objects.get(evento=publico)
        self.assertEqual((registro.usuario, registro.data_inicio), (self.user, publico.data_inicio))

        resp = self.client.post('/api/v1/disponibilidades/por-evento/', {'evento_ids': ids}, format='json')
        self.assertEqual(resp.data, {'criados': 0})
        self.assertEqual(self.client.get('/api/v1/disponibilidades/eventos/').data, [])
        self.assertEqual(self.client.get('/api/v1/disponibilidades/').data[0]['evento'], 'Culto')


class EquipesTests(BaseTestCase):
    def test_lista_e_candidatura(self):
        resp = self.client.get('/api/v1/equipes/')
        self.assertEqual([e['nome'] for e in resp.data['aprovadas']], ['Recepção'])
        self.assertEqual(resp.data['pendentes'], [])
        self.assertEqual([e['nome'] for e in resp.data['disponiveis']], ['Louvor'])

        url = f'/api/v1/equipes/{self.outra_equipe.pk}/candidatura/'
        resp = self.client.post(url)
        self.assertEqual([e['nome'] for e in resp.data['pendentes']], ['Louvor'])
        self.assertEqual(resp.data['disponiveis'], [])
        self.client.post(url)  # repetir não duplica
        membro = MembrosEquipe.objects.get(usuario=self.user, equipe=self.outra_equipe)
        self.assertFalse(membro.aprovado)

        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(MembrosEquipe.objects.filter(pk=membro.pk).exists())

    def test_cancelar_nao_remove_participacao_aprovada(self):
        resp = self.client.delete(f'/api/v1/equipes/{self.minha_equipe.pk}/candidatura/')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'sem_candidatura')
        self.assertTrue(MembrosEquipe.objects.filter(usuario=self.user, equipe=self.minha_equipe).exists())

    def test_equipe_inexistente(self):
        self.assertEqual(self.client.post('/api/v1/equipes/9999/candidatura/').status_code, 404)


class PrimeiroAcessoTests(ApiTestCase):
    """Fluxo do app para conta criada pelo líder: definir senha, aceitar termo, usar."""

    def test_fluxo_completo(self):
        user = criar_usuario(liberado=False)
        self.autenticar(user)
        self.assertEqual(self.client.get('/api/v1/home/').data['code'], 'senha_pendente')

        resp = self.client.post('/api/v1/me/definir-senha/', {'nova_senha': '123'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('nova_senha', resp.data['errors'])  # validadores de senha do Django

        resp = self.client.post('/api/v1/me/definir-senha/', {'nova_senha': 'outra-senha-forte-9'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['precisa_definir_senha'])
        self.assertTrue(resp.data['precisa_aceitar_termo'])
        user.refresh_from_db()
        self.assertTrue(user.check_password('outra-senha-forte-9'))

        self.assertEqual(self.client.get('/api/v1/home/').data['code'], 'termo_pendente')
        self.assertIn('Compromisso', self.client.get('/api/v1/termo/').data['html'])
        resp = self.client.post('/api/v1/me/aceitar-termo/')
        self.assertFalse(resp.data['precisa_aceitar_termo'])

        self.assertEqual(self.client.get('/api/v1/home/').status_code, 200)

    def test_definir_senha_so_no_primeiro_login(self):
        self.autenticar(criar_usuario())
        resp = self.client.post('/api/v1/me/definir-senha/', {'nova_senha': 'outra-senha-forte-9'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'senha_ja_definida')


class TrocarSenhaTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = criar_usuario()
        AuthToken.objects.create(user=self.user)  # outro aparelho
        self.autenticar(self.user)

    def trocar(self, atual, nova):
        return self.client.post(
            '/api/v1/me/trocar-senha/', {'senha_atual': atual, 'nova_senha': nova}, format='json')

    def test_troca_e_desconecta_os_outros_aparelhos(self):
        self.assertEqual(self.trocar('senha-forte-123', 'outra-senha-forte-9').status_code, 204)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('outra-senha-forte-9'))
        self.assertEqual(AuthToken.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.client.get('/api/v1/me/').status_code, 200)  # este aparelho continua

    def test_senha_atual_errada(self):
        resp = self.trocar('errada', 'outra-senha-forte-9')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('senha_atual', resp.data['errors'])
        self.assertEqual(AuthToken.objects.filter(user=self.user).count(), 2)
