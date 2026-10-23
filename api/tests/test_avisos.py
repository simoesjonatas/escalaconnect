"""Caixa de avisos do app: cada notificação fica guardada, com contador de não lidos."""
from datetime import timedelta

from django.utils import timezone

from api.models import Aviso
from api.tasks import limpar_avisos_antigos
from escala import services
from escala.models import Desistencia, Escala
from escalaconnect.notificacoes import pedir_confirmacao
from evento.models import Notification

from .test_conta import criar_usuario
from .test_push import PushTestCase


class CaixaDeAvisosTests(PushTestCase):
    def test_aviso_guardado_e_numero_no_icone(self):
        # Criar a escala no setUp já gerou "Você foi escalado".
        (aviso,) = Aviso.objects.filter(usuario=self.user)
        self.assertEqual((aviso.titulo, aviso.tipo, aviso.escala_id), ('Você foi escalado 🙌', 'escalado', self.escala.pk))

        desistencia = Desistencia.objects.create(escala=self.escala, usuario=self.user, motivo='Viagem')
        with self.captureOnCommitCallbacks(execute=True):
            services.aprovar_desistencia(desistencia)
        (msg,) = self.mensagens()
        self.assertEqual(msg['badge'], 2)  # os dois avisos ainda não lidos

        self.autenticar(self.user)
        resp = self.client.get('/api/v1/avisos/')
        self.assertEqual(resp.data['nao_lidos'], 2)
        self.assertEqual([a['titulo'] for a in resp.data['avisos']], ['Impedimento aceito', 'Você foi escalado 🙌'])
        self.assertEqual(self.client.get('/api/v1/home/').data['avisos_nao_lidos'], 2)

        self.assertEqual(self.client.post('/api/v1/avisos/ler/').data, {'nao_lidos': 0})
        self.assertTrue(all(a['lido'] for a in self.client.get('/api/v1/avisos/').data['avisos']))
        self.assertEqual(self.client.get('/api/v1/home/').data['avisos_nao_lidos'], 0)

    def test_guarda_mesmo_sem_aparelho_e_nao_mostra_de_outro(self):
        sem_app = criar_usuario(username='joao', cpf='11144477735')
        Escala.objects.create(usuario=sem_app, funcao=self.funcao, evento=self.evento)
        self.assertEqual(Aviso.objects.filter(usuario=sem_app).count(), 1)
        self.autenticar(sem_app)
        self.assertEqual(len(self.client.get('/api/v1/avisos/').data['avisos']), 1)

    def test_pedido_repetido_dentro_do_intervalo_nao_duplica(self):
        for _ in range(2):
            with self.captureOnCommitCallbacks(execute=True):
                pedir_confirmacao(self.evento)
        self.assertEqual(
            Aviso.objects.filter(usuario=self.user, purpose=Notification.PURPOSE_CONFIRM).count(), 1)

    def test_limpa_avisos_com_mais_de_60_dias(self):
        antigo = Aviso.objects.get(usuario=self.user)
        Aviso.objects.filter(pk=antigo.pk).update(criado_em=timezone.now() - timedelta(days=61))
        Aviso.objects.create(usuario=self.user, titulo='Novo', corpo='x', tipo='escalado', purpose='escalado')
        self.assertEqual(limpar_avisos_antigos(), 1)
        self.assertEqual(list(Aviso.objects.values_list('titulo', flat=True)), ['Novo'])
