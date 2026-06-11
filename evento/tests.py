from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from equipe.models import Equipe
from escala.models import Funcao, Escala
from evento.models import Evento

User = get_user_model()


class EventosApiTests(TestCase):
    def test_cores_por_status_da_minha_escala(self):
        equipe = Equipe.objects.create(nome="Louvor")
        funcao = Funcao.objects.create(nome="Vocal", equipe=equipe)
        base = now() + timedelta(days=2)
        ev_conf = Evento.objects.create(
            nome="Confirmado", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        ev_pend = Evento.objects.create(
            nome="Pendente",
            data_inicio=base + timedelta(days=1),
            data_fim=base + timedelta(days=1, hours=2),
        )
        ev_outro = Evento.objects.create(
            nome="Outro",
            data_inicio=base + timedelta(days=2),
            data_fim=base + timedelta(days=2, hours=2),
        )

        user = User.objects.create_user(
            username="vol", password="x", cpf="10000003001",
            is_first_login=False, termo_aceito_em=now(),
        )
        Escala.objects.create(usuario=user, funcao=funcao, evento=ev_conf, confirmada=True)
        Escala.objects.create(usuario=user, funcao=funcao, evento=ev_pend, confirmada=False)

        self.client.force_login(user)
        resp = self.client.get(reverse('eventos_api'))
        self.assertEqual(resp.status_code, 200)

        cores = {item['title']: item['backgroundColor'] for item in resp.json()}
        self.assertEqual(cores['Confirmado'], '#2e7d32')  # verde
        self.assertEqual(cores['Pendente'], '#ef6c00')    # laranja
        self.assertEqual(cores['Outro'], '#3b5bdb')       # azul
