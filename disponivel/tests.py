from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from disponivel.models import Disponivel

User = get_user_model()


class HomeAvisoDisponibilidadeTests(TestCase):
    def _user(self, username, cpf):
        return User.objects.create_user(
            username=username, password="x", cpf=cpf,
            is_first_login=False, termo_aceito_em=now(),
        )

    def test_aviso_aparece_quando_sem_disponibilidade(self):
        self.client.force_login(self._user("sem_disp", "10000004001"))
        resp = self.client.get('/')
        self.assertContains(resp, "não cadastrou nenhuma disponibilidade")

    def test_aviso_some_quando_tem_disponibilidade(self):
        user = self._user("com_disp", "10000004002")
        Disponivel.objects.create(
            usuario=user, data_inicio=now(), data_fim=now() + timedelta(hours=2)
        )
        self.client.force_login(user)
        resp = self.client.get('/')
        self.assertNotContains(resp, "não cadastrou nenhuma disponibilidade")
