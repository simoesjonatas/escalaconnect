from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Equipe, Lideranca, MembrosEquipe

User = get_user_model()


class BuscaSelectNosFormulariosTests(TestCase):
    """Adicionar líder e adicionar membro usam o select com busca, com nomes completos em ordem."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome='Recepção')
        self.admin = User.objects.create_user(username='admin', password='x', cpf='52998224725', is_staff=True,
                                              is_first_login=False, termo_aceito_em=timezone.now())
        User.objects.create_user(username='zeca', password='x', cpf='11144477735', first_name='Zeca', last_name='Lima')
        User.objects.create_user(username='ana', password='x', cpf='39053344705', first_name='Ana', last_name='Souza')
        self.client.force_login(self.admin)

    def test_formularios_tem_busca_e_nomes_em_ordem(self):
        for nome in ('lideranca_create', 'membros_equipe_create'):
            resp = self.client.get(reverse(nome, args=[self.equipe.pk]))
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode()
            self.assertIn('data-busca', html)
            self.assertIn('js/busca-select', html)
            self.assertLess(html.index('>Ana Souza<'), html.index('>Zeca Lima<'))

    def test_envio_continua_funcionando(self):
        zeca = User.objects.get(username='zeca')
        self.client.post(reverse('lideranca_create', args=[self.equipe.pk]), {'usuario': zeca.pk, 'equipe': self.equipe.pk})
        self.assertTrue(Lideranca.objects.filter(usuario=zeca, equipe=self.equipe).exists())
        self.client.post(reverse('membros_equipe_create', args=[self.equipe.pk]), {'usuario': zeca.pk, 'equipe': self.equipe.pk})
        self.assertTrue(MembrosEquipe.objects.filter(usuario=zeca, equipe=self.equipe).exists())
