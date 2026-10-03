from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from escala.models import Escala
from evento.models import Evento

User = get_user_model()


class CriarRevisorTests(TestCase):
    def rodar(self, *args):
        saida = StringIO()
        call_command('criar_revisor', *args, stdout=saida)
        return saida.getvalue()

    def test_cria_revisor_pronto_para_usar_o_app(self):
        saida = self.rodar('--senha', 'Senha-Revisao-1')
        revisor = User.objects.get(username='revisor')
        self.assertTrue(revisor.check_password('Senha-Revisao-1'))
        self.assertFalse(revisor.is_first_login)
        self.assertIsNotNone(revisor.termo_aceito_em)
        self.assertTrue(revisor.is_in_team())
        self.assertIn('senha:   Senha-Revisao-1', saida)

        escalas = Escala.objects.filter(evento__nome='Culto de demonstração').order_by('evento__data_inicio')
        self.assertEqual([(e.usuario, e.confirmada) for e in escalas],
                         [(revisor, False), (revisor, True), (None, False)])
        self.assertTrue(all(e.evento.data_inicio > timezone.now() for e in escalas))
        # Os eventos são privados da equipe de demonstração: outro voluntário não os vê.
        outro = User.objects.create_user(username='maria', password='x', cpf='52998224725')
        self.assertFalse(Evento.objects.visiveis_para(outro).filter(nome='Culto de demonstração').exists())

    def test_rodar_de_novo_renova_sem_duplicar(self):
        self.rodar('--senha', 'a')
        self.rodar('--senha', 'b')
        self.assertEqual(User.objects.filter(username='revisor').count(), 1)
        self.assertEqual(Evento.objects.filter(nome='Culto de demonstração').count(), 3)
        self.assertTrue(User.objects.get(username='revisor').check_password('b'))

    def test_gera_senha_quando_nao_informada(self):
        saida = self.rodar()
        senha = saida.split('senha:')[1].split()[0]
        self.assertTrue(User.objects.get(username='revisor').check_password(senha))
