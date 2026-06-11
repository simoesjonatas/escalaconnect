import itertools
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from equipe.models import Equipe, MembrosEquipe
from evento.models import Evento
from escala.models import Funcao, Escala
from disponivel.models import Disponivel
from ocupado.models import Ocupado
from escala.utils import usuarios_disponiveis_para_evento

User = get_user_model()

# Gera CPFs únicos para os testes. Os validadores de CPF só rodam em full_clean(),
# não em create_user(), então qualquer string única de 11 dígitos serve.
_cpf_seq = itertools.count(10000000000)


def criar_usuario(username):
    return User.objects.create_user(
        username=username, password="senha-teste", cpf=str(next(_cpf_seq))
    )


class UsuariosDisponiveisParaEventoTests(TestCase):
    """Cobre o matching central: quem pode ser escalado para um evento."""

    @classmethod
    def setUpTestData(cls):
        cls.equipe = Equipe.objects.create(nome="Louvor")
        cls.funcao = Funcao.objects.create(nome="Vocal", equipe=cls.equipe)
        base = (timezone.now() + timedelta(days=7)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        cls.inicio = base
        cls.fim = base + timedelta(hours=2)
        cls.evento = Evento.objects.create(
            nome="Culto", data_inicio=cls.inicio, data_fim=cls.fim
        )

    def _membro(self, username, aprovado=True):
        user = criar_usuario(username)
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=user, aprovado=aprovado)
        return user

    def _disponivel_cobrindo_o_evento(self, user):
        return Disponivel.objects.create(
            usuario=user,
            data_inicio=self.inicio - timedelta(hours=1),
            data_fim=self.fim + timedelta(hours=1),
        )

    def test_membro_aprovado_e_disponivel_aparece(self):
        user = self._membro("disponivel")
        self._disponivel_cobrindo_o_evento(user)
        ids = usuarios_disponiveis_para_evento(self.equipe, self.evento)
        self.assertIn(user.id, ids)

    def test_membro_nao_aprovado_nao_aparece(self):
        user = self._membro("pendente", aprovado=False)
        self._disponivel_cobrindo_o_evento(user)
        ids = usuarios_disponiveis_para_evento(self.equipe, self.evento)
        self.assertNotIn(user.id, ids)

    def test_sem_disponibilidade_cadastrada_nao_aparece(self):
        user = self._membro("sem_disp")
        ids = usuarios_disponiveis_para_evento(self.equipe, self.evento)
        self.assertNotIn(user.id, ids)

    def test_ocupado_sobreposto_nao_aparece(self):
        user = self._membro("ocupado")
        self._disponivel_cobrindo_o_evento(user)
        Ocupado.objects.create(
            usuario=user,
            data_inicio=self.inicio + timedelta(minutes=30),
            data_fim=self.fim - timedelta(minutes=30),
        )
        ids = usuarios_disponiveis_para_evento(self.equipe, self.evento)
        self.assertNotIn(user.id, ids)

    def test_disponibilidade_parcial_nao_cobre_o_evento(self):
        user = self._membro("parcial")
        # Disponível só na primeira hora; o evento dura duas horas.
        Disponivel.objects.create(
            usuario=user,
            data_inicio=self.inicio - timedelta(hours=1),
            data_fim=self.inicio + timedelta(hours=1),
        )
        ids = usuarios_disponiveis_para_evento(self.equipe, self.evento)
        self.assertNotIn(user.id, ids)

    def test_ja_escalado_no_evento_nao_aparece(self):
        user = self._membro("escalado")
        self._disponivel_cobrindo_o_evento(user)
        Escala.objects.create(usuario=user, funcao=self.funcao, evento=self.evento)
        ids = usuarios_disponiveis_para_evento(self.equipe, self.evento)
        self.assertNotIn(user.id, ids)

    def test_excluir_escala_id_libera_o_proprio_usuario(self):
        user = self._membro("realocar")
        self._disponivel_cobrindo_o_evento(user)
        escala = Escala.objects.create(usuario=user, funcao=self.funcao, evento=self.evento)
        ids = usuarios_disponiveis_para_evento(
            self.equipe, self.evento, excluir_escala_id=escala.id
        )
        self.assertIn(user.id, ids)


class EscalaModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.equipe = Equipe.objects.create(nome="Mídia")
        cls.funcao = Funcao.objects.create(nome="Projeção", equipe=cls.equipe)
        inicio = timezone.now() + timedelta(days=1)
        cls.evento = Evento.objects.create(
            nome="Ensaio", data_inicio=inicio, data_fim=inicio + timedelta(hours=2)
        )

    def test_propriedade_equipe_vem_da_funcao(self):
        escala = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        self.assertEqual(escala.equipe, self.equipe)

    def test_clear_escala_remove_usuario_e_confirmacao(self):
        user = criar_usuario("dono")
        escala = Escala.objects.create(
            usuario=user,
            funcao=self.funcao,
            evento=self.evento,
            confirmada=True,
            data_confirmacao=timezone.now(),
        )
        escala.clear_escala()
        escala.refresh_from_db()
        self.assertIsNone(escala.usuario)
        self.assertFalse(escala.confirmada)
        self.assertIsNone(escala.data_confirmacao)
