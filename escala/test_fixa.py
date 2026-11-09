"""Escala fixa: em quais cultos cada linha vale, preenchimento, mudanças e o aviso de resumo."""
import calendar
from datetime import date, datetime, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from api.models import Aviso
from api.tests.test_conta import criar_usuario
from equipe.models import Equipe, MembrosEquipe
from escala import fixa
from escala.models import Desistencia, Escala, EscalaFixa, EscalaFixaItem, Funcao
from escalaconnect.regras import RegraDeNegocio
from evento import services as evento_services
from evento.models import Evento, Notification
from ocupado.models import Ocupado

DOMINGO, QUARTA = 6, 2
MANHA, NOITE = EscalaFixaItem.TURNO_MANHA, EscalaFixaItem.TURNO_NOITE


def quando(dia, hora, minuto=0):
    return timezone.make_aware(datetime.combine(dia, datetime.min.time()).replace(hour=hora, minute=minuto))


def mes_seguinte():
    hoje = timezone.localdate()
    return (hoje.year + hoje.month // 12, hoje.month % 12 + 1)


def dias_do_mes(ano, mes, dia_semana):
    return [date(ano, mes, d) for d in range(1, calendar.monthrange(ano, mes)[1] + 1)
            if date(ano, mes, d).weekday() == dia_semana]


class TurnoEOcorrenciaTests(TestCase):
    def test_turno_pelo_horario_local(self):
        dia = date(2030, 1, 6)
        self.assertEqual(fixa.turno_de(quando(dia, 9, 45)), MANHA)
        self.assertEqual(fixa.turno_de(quando(dia, 15)), EscalaFixaItem.TURNO_TARDE)
        self.assertEqual(fixa.turno_de(quando(dia, 18)), NOITE)

    def test_ocorrencia_no_mes(self):
        self.assertEqual([fixa.ocorrencia_no_mes(quando(date(2030, 3, d), 10)) for d in (1, 7, 8, 21, 29, 31)],
                         [1, 1, 2, 3, 5, 5])


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class EscalaFixaTestCase(TestCase):
    def setUp(self):
        self.equipe = Equipe.objects.create(nome='Som')
        self.mesa = Funcao.objects.create(nome='Mesa', equipe=self.equipe)
        self.palco = Funcao.objects.create(nome='Palco', equipe=self.equipe)
        self.ana = self.membro('ana', '11144477735')
        self.bia = self.membro('bia', '52998224725')
        self.caio = self.membro('caio', '93541134780')
        self.fixa = EscalaFixa.objects.create(equipe=self.equipe, ativa=True)
        ano, mes = mes_seguinte()
        self.domingos = dias_do_mes(ano, mes, DOMINGO)
        self.manhas = [self.culto('Culto de Domingo - Manhã', d, 9, 45) for d in self.domingos]
        self.noites = [self.culto('Culto de Domingo - Noite', d, 18) for d in self.domingos]

    def membro(self, nome, cpf):
        usuario = criar_usuario(nome, cpf=cpf, first_name=nome.capitalize())
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=usuario, aprovado=True)
        return usuario

    def culto(self, nome, dia, hora, minuto=0, funcoes=None, **extra):
        """Culto com uma vaga de cada função (Mesa e Palco, se não disser outras)."""
        inicio = quando(dia, hora, minuto)
        evento = Evento.objects.create(nome=nome, data_inicio=inicio, data_fim=inicio + timedelta(hours=2), **extra)
        for funcao in (funcoes if funcoes is not None else [self.mesa, self.palco]):
            Escala.objects.create(evento=evento, funcao=funcao)
        return evento

    def linha(self, usuario, funcao=None, dia=DOMINGO, turno=MANHA, semana=0):
        return EscalaFixaItem.objects.create(escala_fixa=self.fixa, dia_semana=dia, turno=turno, semana=semana,
                                             funcao=funcao or self.mesa, usuario=usuario)

    def quem(self, evento, funcao=None):
        return list(Escala.objects.filter(evento=evento, funcao=funcao or self.mesa)
                    .order_by('pk').values_list('usuario__username', flat=True))

    def aplicar(self):
        with self.captureOnCommitCallbacks(execute=True):
            return fixa.aplicar_escala_fixa(self.equipe)


class AplicarTests(EscalaFixaTestCase):
    def test_semana_especifica_substitui_toda_semana_so_nela_e_so_na_funcao(self):
        self.linha(self.ana)
        self.linha(self.bia, semana=3)
        self.linha(self.caio, funcao=self.palco)
        resultado = self.aplicar()

        esperado = [['bia'] if i == 2 else ['ana'] for i in range(len(self.manhas))]
        self.assertEqual([self.quem(e) for e in self.manhas], esperado)
        # A outra função continua com a linha de "todo domingo", inclusive no 3º domingo.
        self.assertEqual([self.quem(e, self.palco) for e in self.manhas], [['caio']] * len(self.manhas))
        self.assertEqual([self.quem(e) for e in self.noites], [[None]] * len(self.noites))
        self.assertEqual(resultado['preenchidas'], 2 * len(self.manhas))

    def test_semana_sem_linha_e_sem_toda_semana_fica_intocada(self):
        self.linha(self.ana, semana=1)
        self.aplicar()
        self.assertEqual(self.quem(self.manhas[0]), ['ana'])
        self.assertEqual([self.quem(e) for e in self.manhas[1:]], [[None]] * (len(self.manhas) - 1))

    def test_usa_a_vaga_do_culto_e_nao_repete(self):
        self.linha(self.ana)
        self.linha(self.bia, funcao=self.palco)
        self.aplicar()
        self.aplicar()
        self.assertEqual(self.quem(self.manhas[0]), ['ana'])
        self.assertEqual(self.quem(self.manhas[0], self.palco), ['bia'])
        self.assertEqual(Escala.objects.filter(evento=self.manhas[0]).count(), 2)

    def test_desligada_nao_preenche(self):
        self.fixa.ativa = False
        self.fixa.save()
        self.linha(self.ana)
        self.assertEqual(self.aplicar()['preenchidas'], 0)
        self.assertFalse(Escala.objects.filter(usuario__isnull=False).exists())

    def test_eventos_passados_e_de_outra_equipe_ficam_de_fora(self):
        outra = Equipe.objects.create(nome='Louvor')
        privado = self.culto('Ensaio', self.domingos[0] + timedelta(days=7 * 5), 9, equipe=outra)
        passado = self.culto('Culto antigo', timezone.localdate() - timedelta(days=timezone.localdate().weekday() + 1), 9)
        self.linha(self.ana)
        self.aplicar()
        self.assertEqual(self.quem(privado), [None])
        self.assertEqual(self.quem(passado), [None])

    def test_impedimento_aprovado_e_troca_do_lider_valem(self):
        self.linha(self.ana)
        self.aplicar()
        primeira, segunda = (Escala.objects.get(evento=e, funcao=self.mesa) for e in self.manhas[:2])
        primeira.clear_escala()  # impedimento aprovado: vira vaga
        segunda.usuario = self.caio  # o líder trocou
        segunda.save()
        self.aplicar()
        self.assertEqual(self.quem(self.manhas[0]), [None])
        self.assertEqual(self.quem(self.manhas[1]), ['caio'])

    def test_so_entra_no_culto_que_tem_a_funcao(self):
        especial = self.culto('Conferência', self.domingos[0] + timedelta(days=7 * 5), 9, funcoes=[self.palco])
        self.linha(self.ana)
        self.linha(self.bia, funcao=self.palco)
        self.aplicar()
        self.assertEqual(self.quem(especial), [])  # sem Mesa no culto: a linha da Mesa não entra
        self.assertEqual(self.quem(especial, self.palco), ['bia'])

    def test_duas_pessoas_na_mesma_funcao_criam_a_vaga_que_falta(self):
        self.linha(self.ana)
        self.linha(self.bia)
        self.aplicar()
        self.assertEqual(sorted(self.quem(self.manhas[0])), ['ana', 'bia'])

    def test_pula_quem_nao_pode_e_deixa_a_vaga(self):
        louvor = Equipe.objects.create(nome='Louvor')
        Escala.objects.create(evento=self.manhas[0], usuario=self.ana,
                              funcao=Funcao.objects.create(nome='Voz', equipe=louvor))
        Ocupado.objects.create(usuario=self.ana, data_inicio=self.manhas[1].data_inicio - timedelta(hours=1),
                               data_fim=self.manhas[1].data_fim)
        self.linha(self.ana)
        self.linha(self.bia, funcao=self.palco)
        MembrosEquipe.objects.filter(usuario=self.bia).delete()

        resultado = self.aplicar()
        motivos = sorted({p['motivo'].split(' (')[0] for p in resultado['puladas']})
        self.assertEqual(motivos, ['já está escalado neste culto', 'marcou que está ocupado nesse horário',
                                   'não é mais membro da equipe'])
        self.assertEqual(self.quem(self.manhas[0]), [None])
        self.assertEqual(self.quem(self.manhas[1]), [None])
        self.assertEqual(self.quem(self.manhas[2]), ['ana'])
        # Na segunda vez não tenta de novo nem repete o aviso ao líder.
        self.assertEqual(self.aplicar()['puladas'], [])


class AvisoDeResumoTests(EscalaFixaTestCase):
    def test_um_aviso_so_para_varios_cultos(self):
        self.linha(self.ana)
        self.aplicar()
        avisos = Aviso.objects.filter(usuario=self.ana)
        self.assertEqual(avisos.count(), 1)
        aviso = avisos.get()
        self.assertEqual(aviso.purpose, Notification.PURPOSE_FIXED_ASSIGNED)
        self.assertEqual(aviso.titulo, 'Você está na escala fixa 🙌')
        self.assertIn(f'{len(self.manhas)} cultos em', aviso.corpo)
        self.assertIn('Mesa', aviso.corpo)
        self.assertFalse(Escala.objects.filter(aviso_pendente=True).exists())

    def test_um_culto_so_vira_o_aviso_normal(self):
        self.linha(self.ana, semana=1)
        self.aplicar()
        aviso = Aviso.objects.get(usuario=self.ana)
        self.assertEqual((aviso.titulo, aviso.purpose), ('Você foi escalado 🙌', Notification.PURPOSE_ASSIGNED))
        self.assertEqual(aviso.escala_id, Escala.objects.get(usuario=self.ana).pk)


class CadastroDeCultoTests(EscalaFixaTestCase):
    def test_culto_novo_ja_sai_preenchido_e_sem_vaga_duplicada(self):
        self.linha(self.ana)
        self.linha(self.bia, turno=NOITE, dia=QUARTA)
        quarta = dias_do_mes(*mes_seguinte(), QUARTA)[0]
        with self.captureOnCommitCallbacks(execute=True):
            evento = evento_services.criar_evento(
                'Culto de Quarta', None, quando(quarta, 19, 30), quando(quarta, 21), funcoes=[self.mesa, self.palco])
        self.assertEqual(self.quem(evento), ['bia'])
        self.assertEqual(self.quem(evento, self.palco), [None])

    def test_em_massa_preenche_todos(self):
        self.linha(self.ana, turno=NOITE, dia=QUARTA)
        with self.captureOnCommitCallbacks(execute=True):
            eventos, _ = evento_services.gerar_eventos_em_massa(
                'Culto de Quarta', None, ['%d-%02d' % mes_seguinte()], [QUARTA],
                datetime.strptime('19:30', '%H:%M').time(), datetime.strptime('21:00', '%H:%M').time(),
                funcoes=[self.mesa])
        self.assertEqual([self.quem(e) for e in eventos], [['ana']] * len(eventos))
        self.assertEqual(Aviso.objects.filter(usuario=self.ana).count(), 1)

    def test_culto_sem_a_funcao_so_preenche_quando_a_funcao_entra(self):
        self.linha(self.ana)
        with self.captureOnCommitCallbacks(execute=True):
            evento = evento_services.criar_evento('Culto', None, quando(self.domingos[0], 10),
                                                  quando(self.domingos[0], 12))
        self.assertEqual(self.quem(evento), [])
        with self.captureOnCommitCallbacks(execute=True):
            evento_services.aplicar_funcoes([evento], [self.mesa])
        self.assertEqual(self.quem(evento), ['ana'])
        with self.captureOnCommitCallbacks(execute=True):
            Escala.objects.create(evento=evento, funcao=self.palco)  # pelo site, uma vaga por vez
        self.assertEqual(self.quem(evento, self.palco), [None])  # Palco não tem linha

    def test_equipe_flexivel_nao_e_afetada(self):
        self.fixa.ativa = False
        self.fixa.save()
        self.linha(self.ana)
        with self.captureOnCommitCallbacks(execute=True):
            evento = evento_services.criar_evento('Culto', None, quando(self.domingos[0], 10),
                                                  quando(self.domingos[0], 12), funcoes=[self.mesa])
        self.assertEqual(self.quem(evento), [None])


class MudarAConfiguracaoTests(EscalaFixaTestCase):
    def test_validacoes(self):
        outra = Funcao.objects.create(nome='Porta', equipe=Equipe.objects.create(nome='Recepção'))
        fora = criar_usuario('zeca', cpf='39053344705')
        casos = [
            ({'funcao': outra}, 'funcao_de_outra_equipe'),
            ({'usuario': fora}, 'nao_membro'),
            ({'turno': 'madrugada'}, 'turno_invalido'),
            ({'semana': 6}, 'semana_invalida'),
        ]
        for mudanca, code in casos:
            dados = {'dia_semana': DOMINGO, 'turno': MANHA, 'semana': 0, 'funcao': self.mesa, 'usuario': self.ana,
                     **mudanca}
            with self.subTest(code=code), self.assertRaises(RegraDeNegocio) as erro:
                fixa.adicionar_item(self.equipe, **dados)
            self.assertEqual(erro.exception.code, code)

        fixa.adicionar_item(self.equipe, DOMINGO, MANHA, 0, self.mesa, self.ana)
        with self.assertRaises(RegraDeNegocio) as erro:
            fixa.adicionar_item(self.equipe, DOMINGO, MANHA, 0, self.mesa, self.ana)
        self.assertEqual(erro.exception.code, 'linha_repetida')

    def test_trocar_a_pessoa_muda_so_as_nao_confirmadas(self):
        item = self.linha(self.ana)
        self.aplicar()
        confirmada = Escala.objects.get(evento=self.manhas[0], funcao=self.mesa)
        confirmada.confirmada = True
        confirmada.save()
        Aviso.objects.all().delete()

        with self.captureOnCommitCallbacks(execute=True):
            resultado = fixa.atualizar_item(item, DOMINGO, MANHA, 0, self.mesa, self.bia)

        self.assertEqual(self.quem(self.manhas[0]), ['ana'])
        self.assertEqual([self.quem(e) for e in self.manhas[1:]], [['bia']] * (len(self.manhas) - 1))
        self.assertEqual(len(resultado['nao_alteradas']), 1)
        saiu = Aviso.objects.get(usuario=self.ana)
        self.assertEqual((saiu.titulo, saiu.purpose), ('Sua escala mudou', Notification.PURPOSE_FIXED_CHANGED))
        self.assertEqual(Aviso.objects.get(usuario=self.bia).purpose, Notification.PURPOSE_FIXED_ASSIGNED)

    def test_mudar_so_a_semana_nao_avisa_quem_continua(self):
        item = self.linha(self.ana)
        self.aplicar()
        Aviso.objects.all().delete()
        with self.captureOnCommitCallbacks(execute=True):
            resultado = fixa.atualizar_item(item, DOMINGO, MANHA, 1, self.mesa, self.ana)
        self.assertEqual(self.quem(self.manhas[0]), ['ana'])
        self.assertEqual([self.quem(e) for e in self.manhas[1:]], [[None]] * (len(self.manhas) - 1))
        self.assertEqual(resultado['liberadas'], len(self.manhas) - 1)
        self.assertEqual(Aviso.objects.get(usuario=self.ana).corpo,
                         f'Você não serve mais em {len(self.manhas) - 1} cultos da escala fixa')

    def test_excluir_linha_libera_as_vagas_e_mantem_pedido_pendente(self):
        item = self.linha(self.ana)
        self.aplicar()
        com_pedido = Escala.objects.get(evento=self.manhas[1], funcao=self.mesa)
        Desistencia.objects.create(escala=com_pedido, usuario=self.ana, motivo='Viagem')
        with self.captureOnCommitCallbacks(execute=True):
            resultado = fixa.excluir_item(item)
        self.assertEqual(self.quem(self.manhas[1]), ['ana'])
        self.assertEqual(self.quem(self.manhas[0]), [None])
        self.assertEqual(resultado['nao_alteradas'][0]['motivo'], 'tem um pedido à espera')
        self.assertFalse(EscalaFixaItem.objects.exists())

    def test_ligar_preenche_os_cultos_cadastrados(self):
        self.fixa.ativa = False
        self.fixa.save()
        self.linha(self.ana)
        with self.captureOnCommitCallbacks(execute=True):
            resultado = fixa.definir_ativa(self.equipe, True)
        self.assertEqual(resultado['preenchidas'], len(self.manhas))
        self.assertIn('cultos preenchidos', fixa.descrever_resultado(resultado))
