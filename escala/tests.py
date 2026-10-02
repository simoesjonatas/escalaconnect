import calendar
import itertools
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from equipe.models import Equipe, MembrosEquipe, Lideranca
from evento.models import Evento
from escala.models import Funcao, Escala, Desistencia, SolicitacaoTroca
from planejamento.models import Planejamento, PlanejamentoFuncao
from disponivel.models import Disponivel
from ocupado.models import Ocupado
from escala.utils import usuarios_disponiveis_para_evento, preencher_vagas

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


class AutoEscalarEventoTests(TestCase):
    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Louvor AE")
        self.funcao = Funcao.objects.create(nome="Vocal", equipe=self.equipe)
        self.base = (timezone.now() + timedelta(days=7)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        self.evento = Evento.objects.create(
            nome="Culto AE", data_inicio=self.base, data_fim=self.base + timedelta(hours=2)
        )
        self.ana = self._membro_disponivel("ana_ae")
        self.bia = self._membro_disponivel("bia_ae")

        # 'ana' já serviu num evento recente -> carga maior, deve ser preterida
        recente = timezone.now() - timedelta(days=3)
        ev_recente = Evento.objects.create(
            nome="Ensaio AE", data_inicio=recente, data_fim=recente + timedelta(hours=1)
        )
        Escala.objects.create(usuario=self.ana, funcao=self.funcao, evento=ev_recente)

        # vaga em aberto no evento alvo
        self.vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)

        self.lider = criar_usuario("lider_ae")
        self.lider.is_first_login = False
        self.lider.termo_aceito_em = timezone.now()
        self.lider.save()
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)

    def _membro_disponivel(self, username):
        user = criar_usuario(username)
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=user, aprovado=True)
        Disponivel.objects.create(
            usuario=user,
            data_inicio=self.base - timedelta(hours=1),
            data_fim=self.base + timedelta(hours=3),
        )
        return user

    def test_preenche_vaga_priorizando_menos_sobrecarregado(self):
        self.client.force_login(self.lider)
        resp = self.client.post(reverse('auto_escalar_evento', args=[self.evento.pk]))
        self.assertEqual(resp.status_code, 302)
        self.vaga.refresh_from_db()
        self.assertEqual(self.vaga.usuario, self.bia)  # carga 0 sobre carga 1

    def test_sem_permissao_retorna_403(self):
        estranho = criar_usuario("estranho_ae")
        estranho.is_first_login = False
        estranho.termo_aceito_em = timezone.now()
        estranho.save()
        self.client.force_login(estranho)
        resp = self.client.post(reverse('auto_escalar_evento', args=[self.evento.pk]))
        self.assertEqual(resp.status_code, 403)
        self.vaga.refresh_from_db()
        self.assertIsNone(self.vaga.usuario)

    def test_auto_escalar_equipe_preenche_vagas_futuras(self):
        self.client.force_login(self.lider)
        resp = self.client.post(reverse('auto_escalar_equipe', args=[self.equipe.pk]))
        self.assertEqual(resp.status_code, 302)
        self.vaga.refresh_from_db()
        self.assertEqual(self.vaga.usuario, self.bia)


class PreencherVagasRegrasTests(TestCase):
    """Regras de justiça da auto-escala: teto mensal e prioridade por escassez."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Louvor Regras")
        self.funcao = Funcao.objects.create(nome="Vocal", equipe=self.equipe)
        # Dia 15 de um mês futuro: garante folga para criar datas vizinhas
        # (dias 5, 8, 20, 25) dentro do MESMO mês do evento alvo.
        self.base = (timezone.now() + timedelta(days=40)).replace(
            day=15, hour=10, minute=0, second=0, microsecond=0
        )
        self.evento = Evento.objects.create(
            nome="Culto Regras",
            data_inicio=self.base,
            data_fim=self.base + timedelta(hours=2),
        )

    def _membro(self, username):
        user = criar_usuario(username)
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=user, aprovado=True)
        return user

    def _disp_cobrindo_evento(self, user):
        return Disponivel.objects.create(
            usuario=user,
            data_inicio=self.base - timedelta(hours=1),
            data_fim=self.base + timedelta(hours=3),
        )

    def _disp_avulsa_no_mes(self, user, dia):
        inicio = self.base.replace(day=dia)
        Disponivel.objects.create(
            usuario=user, data_inicio=inicio, data_fim=inicio + timedelta(hours=2)
        )

    def _escala_no_mes(self, user, dia):
        inicio = self.base.replace(day=dia)
        ev = Evento.objects.create(
            nome=f"Ev {dia}", data_inicio=inicio, data_fim=inicio + timedelta(hours=1)
        )
        return Escala.objects.create(usuario=user, funcao=self.funcao, evento=ev)

    def test_regra2_prioriza_quem_tem_menos_disponibilidade_no_mes(self):
        # so_um marcou apenas o dia do evento; flexivel marcou vários dias.
        # Ambos com carga 0 -> deve vencer quem tem menos disponibilidade.
        so_um = self._membro("so_um")
        self._disp_cobrindo_evento(so_um)

        flexivel = self._membro("flexivel")
        self._disp_cobrindo_evento(flexivel)
        for dia in (5, 8, 20, 25):
            self._disp_avulsa_no_mes(flexivel, dia)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        preenchidas = preencher_vagas([vaga])

        self.assertEqual(preenchidas, 1)
        vaga.refresh_from_db()
        self.assertEqual(vaga.usuario, so_um)

    def test_regra1_teto_mensal_exclui_mesmo_com_disponibilidade(self):
        # cheio já tem 2 escalas no mês e MENOS disponibilidade -> sem o teto ele
        # venceria; com o teto é excluído e a vaga vai para livre.
        cheio = self._membro("cheio")
        self._disp_cobrindo_evento(cheio)
        self._escala_no_mes(cheio, 5)
        self._escala_no_mes(cheio, 8)

        livre = self._membro("livre")
        self._disp_cobrindo_evento(livre)
        for dia in (5, 8, 20, 25):
            self._disp_avulsa_no_mes(livre, dia)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        preenchidas = preencher_vagas([vaga])

        self.assertEqual(preenchidas, 1)
        vaga.refresh_from_db()
        self.assertEqual(vaga.usuario, livre)

    def test_regra1_deixa_vaga_vazia_quando_todos_no_teto(self):
        pessoa = self._membro("no_teto")
        self._disp_cobrindo_evento(pessoa)
        self._escala_no_mes(pessoa, 5)
        self._escala_no_mes(pessoa, 8)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        preenchidas = preencher_vagas([vaga])

        self.assertEqual(preenchidas, 0)
        vaga.refresh_from_db()
        self.assertIsNone(vaga.usuario)

    def test_limite_por_mes_configuravel(self):
        # Com teto = 1, quem já tem 1 escala no mês é barrado.
        um = self._membro("uma_escala")
        self._disp_cobrindo_evento(um)
        self._escala_no_mes(um, 5)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        preenchidas = preencher_vagas([vaga], limite_por_mes=1)

        self.assertEqual(preenchidas, 0)
        vaga.refresh_from_db()
        self.assertIsNone(vaga.usuario)

    def test_teto_conta_mes_no_fuso_local_para_evento_de_fim_de_mes(self):
        # Culto no último dia do mês, à noite: em UTC já é dia 1 do mês seguinte.
        # O teto mensal precisa contar pelo mês LOCAL, senão as escalas do mês
        # não seriam vistas e o voluntário seria escalado além do teto.
        tz = timezone.get_current_timezone()
        futuro = timezone.localtime() + timedelta(days=60)
        ano, mes = futuro.year, futuro.month
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        inicio_local = timezone.make_aware(datetime(ano, mes, ultimo_dia, 23, 30), tz)
        evento_fim = Evento.objects.create(
            nome="Culto fim de mês",
            data_inicio=inicio_local,
            data_fim=inicio_local + timedelta(hours=1),
        )

        cheio = self._membro("cheio_fim_mes")
        Disponivel.objects.create(
            usuario=cheio,
            data_inicio=inicio_local - timedelta(hours=1),
            data_fim=inicio_local + timedelta(hours=2),
        )
        # Duas escalas no começo do MESMO mês local -> teto já atingido.
        for dia in (3, 5):
            ini = timezone.make_aware(datetime(ano, mes, dia, 10, 0), tz)
            ev = Evento.objects.create(
                nome=f"Ev {dia}", data_inicio=ini, data_fim=ini + timedelta(hours=1)
            )
            Escala.objects.create(usuario=cheio, funcao=self.funcao, evento=ev)

        vaga = Escala.objects.create(funcao=self.funcao, evento=evento_fim)
        # Recarrega do banco (como a view faz): o datetime volta em UTC, é aí que
        # o mês divergiria se não convertêssemos para o fuso local.
        vagas = list(
            Escala.objects.filter(pk=vaga.pk)
            .select_related('evento', 'funcao', 'funcao__equipe')
        )
        preenchidas = preencher_vagas(vagas)

        self.assertEqual(preenchidas, 0)
        vaga.refresh_from_db()
        self.assertIsNone(vaga.usuario)


class ContadorServicosNoMesTests(TestCase):
    """A tela de detalhe da escala mostra quantas vezes cada disponível já
    serviu no mês na equipe, destacando quem atingiu o teto."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Louvor CT")
        self.funcao = Funcao.objects.create(nome="Vocal", equipe=self.equipe)
        self.base = (timezone.now() + timedelta(days=40)).replace(
            day=15, hour=10, minute=0, second=0, microsecond=0
        )
        self.evento = Evento.objects.create(
            nome="Culto CT", data_inicio=self.base, data_fim=self.base + timedelta(hours=2)
        )
        self.lider = criar_usuario("lider_ct")
        self.lider.is_first_login = False
        self.lider.termo_aceito_em = timezone.now()
        self.lider.save()
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)

    def _membro_disponivel(self, username):
        user = criar_usuario(username)
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=user, aprovado=True)
        Disponivel.objects.create(
            usuario=user,
            data_inicio=self.base - timedelta(hours=1),
            data_fim=self.base + timedelta(hours=3),
        )
        return user

    def test_conta_servicos_do_mes_e_destaca_quem_atingiu_o_teto(self):
        ana = self._membro_disponivel("ana_ct")     # servirá 2x no mês -> teto
        bia = self._membro_disponivel("bia_ct")     # 0x no mês
        for offset in (2, 4):
            ini = self.base + timedelta(days=offset)
            ev = Evento.objects.create(
                nome=f"Outro {offset}", data_inicio=ini, data_fim=ini + timedelta(hours=1)
            )
            Escala.objects.create(usuario=ana, funcao=self.funcao, evento=ev)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        self.client.force_login(self.lider)
        resp = self.client.get(
            reverse('escala_detail_equipe', args=[self.equipe.pk, vaga.pk])
        )
        self.assertEqual(resp.status_code, 200)

        contagem = {u.username: u.servicos_no_mes for u in resp.context['usuarios_disponiveis']}
        self.assertEqual(contagem.get("ana_ct"), 2)
        self.assertEqual(contagem.get("bia_ct"), 0)
        # 'ana' bateu o teto padrão (2) -> badge destacado aparece no HTML.
        self.assertContains(resp, "servico-badge--cheio")

    def test_nao_conta_servicos_de_outra_equipe(self):
        ana = self._membro_disponivel("ana_ct2")
        outra_equipe = Equipe.objects.create(nome="Outra CT")
        outra_funcao = Funcao.objects.create(nome="Som", equipe=outra_equipe)
        ini = self.base + timedelta(days=2)
        ev = Evento.objects.create(
            nome="Evento outra equipe", data_inicio=ini, data_fim=ini + timedelta(hours=1)
        )
        Escala.objects.create(usuario=ana, funcao=outra_funcao, evento=ev)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        self.client.force_login(self.lider)
        resp = self.client.get(
            reverse('escala_detail_equipe', args=[self.equipe.pk, vaga.pk])
        )
        contagem = {u.username: u.servicos_no_mes for u in resp.context['usuarios_disponiveis']}
        self.assertEqual(contagem.get("ana_ct2"), 0)  # escala é de outra equipe

    def test_conta_servicos_tambem_para_escalados_no_evento(self):
        outra_funcao = Funcao.objects.create(nome="Guitarra", equipe=self.equipe)
        carla = criar_usuario("carla_ct")
        MembrosEquipe.objects.create(equipe=self.equipe, usuario=carla, aprovado=True)
        # carla já escalada em outra função DESTE evento -> aparece em "escalados"
        Escala.objects.create(usuario=carla, funcao=outra_funcao, evento=self.evento)
        # e mais uma escala no mesmo mês -> total 2 (inclui a deste evento)
        ini = self.base + timedelta(days=3)
        ev = Evento.objects.create(
            nome="Outro C", data_inicio=ini, data_fim=ini + timedelta(hours=1)
        )
        Escala.objects.create(usuario=carla, funcao=self.funcao, evento=ev)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        self.client.force_login(self.lider)
        resp = self.client.get(
            reverse('escala_detail_equipe', args=[self.equipe.pk, vaga.pk])
        )
        self.assertEqual(resp.status_code, 200)
        escalados = {
            e.usuario.username: e.usuario.servicos_no_mes
            for e in resp.context['usuarios_escalados']
        }
        self.assertEqual(escalados.get("carla_ct"), 2)

    def test_conta_servicos_na_pagina_de_escala_por_evento(self):
        # Mesma informação na tela /api/events/<pk>/detail (view escala_detail).
        ana = self._membro_disponivel("ana_ev")
        for offset in (2, 4):
            ini = self.base + timedelta(days=offset)
            ev = Evento.objects.create(
                nome=f"O {offset}", data_inicio=ini, data_fim=ini + timedelta(hours=1)
            )
            Escala.objects.create(usuario=ana, funcao=self.funcao, evento=ev)

        vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)
        self.client.force_login(self.lider)
        resp = self.client.get(reverse('escala_detail', args=[vaga.pk]))
        self.assertEqual(resp.status_code, 200)
        contagem = {u.username: u.servicos_no_mes for u in resp.context['page_obj'].object_list}
        self.assertEqual(contagem.get("ana_ev"), 2)
        self.assertContains(resp, "servico-badge--cheio")


class AplicarFuncoesEventosTests(TestCase):
    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Recepção")
        self.funcao_porta = Funcao.objects.create(nome="Porta", equipe=self.equipe)
        self.funcao_cafe = Funcao.objects.create(nome="Café", equipe=self.equipe)
        self.lider = criar_usuario("lider_funcoes")
        self.lider.is_first_login = False
        self.lider.termo_aceito_em = timezone.now()
        self.lider.save()
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)

        inicio = timezone.now() + timedelta(days=5)
        self.evento_1 = Evento.objects.create(
            nome="Culto 1", data_inicio=inicio, data_fim=inicio + timedelta(hours=2)
        )
        self.evento_2 = Evento.objects.create(
            nome="Culto 2", data_inicio=inicio + timedelta(days=1), data_fim=inicio + timedelta(days=1, hours=2)
        )

    def test_lider_aplica_funcoes_em_varios_eventos_sem_duplicar(self):
        Escala.objects.create(evento=self.evento_1, funcao=self.funcao_porta)
        self.client.force_login(self.lider)

        resp = self.client.post(reverse('aplicar_funcoes_eventos'), {
            'equipes': [self.equipe.pk],
            'eventos': [self.evento_1.pk, self.evento_2.pk],
            'funcoes': [self.funcao_porta.pk, self.funcao_cafe.pk],
        })

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Escala.objects.filter(evento=self.evento_1, funcao=self.funcao_porta).count(), 1)
        self.assertTrue(Escala.objects.filter(evento=self.evento_1, funcao=self.funcao_cafe).exists())
        self.assertTrue(Escala.objects.filter(evento=self.evento_2, funcao=self.funcao_porta).exists())
        self.assertTrue(Escala.objects.filter(evento=self.evento_2, funcao=self.funcao_cafe).exists())

    def test_aplica_funcoes_de_planejamento(self):
        planejamento = Planejamento.objects.create(nome="Domingo manhã")
        PlanejamentoFuncao.objects.create(planejamento=planejamento, funcao=self.funcao_porta)

        self.client.force_login(self.lider)
        resp = self.client.post(reverse('aplicar_funcoes_eventos'), {
            'planejamento': planejamento.pk,
            'eventos': [self.evento_1.pk],
        })

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Escala.objects.filter(evento=self.evento_1, funcao=self.funcao_porta).exists())

    def test_filtro_lista_eventos_publicos_e_apenas_da_equipe_liderada(self):
        outra_equipe = Equipe.objects.create(nome="Outra equipe")
        inicio = timezone.now() + timedelta(days=7)
        evento_da_equipe = Evento.objects.create(
            nome="Evento da recepção",
            equipe=self.equipe,
            data_inicio=inicio,
            data_fim=inicio + timedelta(hours=2),
        )
        evento_de_outra_equipe = Evento.objects.create(
            nome="Evento privado de outra equipe",
            equipe=outra_equipe,
            data_inicio=inicio,
            data_fim=inicio + timedelta(hours=2),
        )

        self.client.force_login(self.lider)
        resp = self.client.get(reverse('aplicar_funcoes_eventos'))

        self.assertEqual(resp.status_code, 200)
        eventos = resp.context['eventos']
        self.assertIn(self.evento_1, eventos)
        self.assertIn(evento_da_equipe, eventos)
        self.assertNotIn(evento_de_outra_equipe, eventos)
        self.assertContains(resp, 'Somente públicos')
        self.assertContains(resp, 'Da equipe')


class PaginasEscalacaoSmokeTests(TestCase):
    """Smoke tests das páginas de escalação (evento e equipe) após a repaginação."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Smoke")
        self.funcao = Funcao.objects.create(nome="Som", equipe=self.equipe)
        base = (timezone.now() + timedelta(days=4)).replace(
            hour=19, minute=0, second=0, microsecond=0
        )
        self.evento = Evento.objects.create(
            nome="Evento Smoke", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        self.vaga = Escala.objects.create(funcao=self.funcao, evento=self.evento)

        self.lider = criar_usuario("lider_smoke")
        self.lider.is_first_login = False
        self.lider.termo_aceito_em = timezone.now()
        self.lider.save()
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)

    def test_escala_detail_evento_renderiza(self):
        self.client.force_login(self.lider)
        resp = self.client.get(reverse('escala_detail', args=[self.vaga.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Vaga em aberto")

    def test_escala_detail_equipe_renderiza(self):
        self.client.force_login(self.lider)
        resp = self.client.get(
            reverse('escala_detail_equipe', args=[self.equipe.pk, self.vaga.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Vaga em aberto")


class MinhasEscalasPageTests(TestCase):
    """Smoke test da página Minhas Escalas após a repaginação em cards."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Recepção ME")
        self.funcao = Funcao.objects.create(nome="Porta", equipe=self.equipe)
        base = (timezone.now() + timedelta(days=3)).replace(
            hour=19, minute=0, second=0, microsecond=0
        )
        self.evento = Evento.objects.create(
            nome="Culto ME", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        self.user = criar_usuario("vol_me")
        self.user.is_first_login = False
        self.user.termo_aceito_em = timezone.now()
        self.user.save()
        Escala.objects.create(usuario=self.user, funcao=self.funcao, evento=self.evento)

    def test_renderiza_cards_com_acao_de_confirmar(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('minhas_escalas'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Culto ME")
        self.assertContains(resp, "A confirmar")
        self.assertContains(resp, "Confirmar")
        self.assertContains(resp, "Baixar agenda (.ics)")

    def test_estado_vazio_sem_escalas(self):
        outro = criar_usuario("sem_escalas_me")
        outro.is_first_login = False
        outro.termo_aceito_em = timezone.now()
        outro.save()
        self.client.force_login(outro)
        resp = self.client.get(reverse('minhas_escalas'))
        self.assertContains(resp, "Você não tem escalas futuras")


class MinhaEscalaDetailPageTests(TestCase):
    """Smoke test do detalhe da minha escala após a repaginação."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Som MED")
        self.funcao = Funcao.objects.create(nome="Mesa", equipe=self.equipe)
        base = (timezone.now() + timedelta(days=5)).replace(
            hour=18, minute=0, second=0, microsecond=0
        )
        self.evento = Evento.objects.create(
            nome="Culto MED", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        self.user = criar_usuario("vol_med")
        self.user.is_first_login = False
        self.user.termo_aceito_em = timezone.now()
        self.user.save()
        self.escala = Escala.objects.create(
            usuario=self.user, funcao=self.funcao, evento=self.evento
        )

    def test_pendente_mostra_confirmar_e_desistencia(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('minha_escala_detail', args=[self.escala.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Culto MED")
        self.assertContains(resp, "Confirmar escala")
        self.assertContains(resp, "Não vai poder servir?")

    def test_confirmada_mostra_sinalizar_impedimento(self):
        self.escala.confirmada = True
        self.escala.data_confirmacao = timezone.now()
        self.escala.save()
        self.client.force_login(self.user)
        resp = self.client.get(reverse('minha_escala_detail', args=[self.escala.pk]))
        self.assertContains(resp, "Sinalizar impedimento")
        self.assertNotContains(resp, "Confirmar escala")

    def test_escala_de_outro_usuario_retorna_404(self):
        outro = criar_usuario("intruso_med")
        outro.is_first_login = False
        outro.termo_aceito_em = timezone.now()
        outro.save()
        self.client.force_login(outro)
        resp = self.client.get(reverse('minha_escala_detail', args=[self.escala.pk]))
        # O projeto usa handler404 customizado que redireciona para a home,
        # então o Http404 do get_object_or_404 vira 302 (e não 404 cru).
        self.assertEqual(resp.status_code, 302)


class MinhaAgendaIcsTests(TestCase):
    """A agenda .ics deve conter só escalas de hoje para frente."""

    def test_ics_so_inclui_eventos_futuros(self):
        equipe = Equipe.objects.create(nome="Som ICS")
        funcao = Funcao.objects.create(nome="Mesa", equipe=equipe)
        user = criar_usuario("vol_ics")
        user.is_first_login = False
        user.termo_aceito_em = timezone.now()
        user.save()

        passado = Evento.objects.create(
            nome="Evento Passado ICS",
            data_inicio=timezone.now() - timedelta(days=10),
            data_fim=timezone.now() - timedelta(days=10) + timedelta(hours=2),
        )
        futuro = Evento.objects.create(
            nome="Evento Futuro ICS",
            data_inicio=timezone.now() + timedelta(days=10),
            data_fim=timezone.now() + timedelta(days=10) + timedelta(hours=2),
        )
        Escala.objects.create(usuario=user, funcao=funcao, evento=passado)
        Escala.objects.create(usuario=user, funcao=funcao, evento=futuro)

        self.client.force_login(user)
        resp = self.client.get(reverse('minha_agenda_ics'))

        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8')
        self.assertIn('Evento Futuro ICS', body)
        self.assertNotIn('Evento Passado ICS', body)


class AprovacaoDesistenciaETrocaPermissaoTests(TestCase):
    """Só a liderança da equipe da escala (ou staff) analisa/aprova desistências e trocas."""

    def setUp(self):
        self.equipe = Equipe.objects.create(nome="Recepção AP")
        self.outra_equipe = Equipe.objects.create(nome="Som AP")
        self.funcao = Funcao.objects.create(nome="Porta", equipe=self.equipe)
        base = (timezone.now() + timedelta(days=4)).replace(
            hour=19, minute=0, second=0, microsecond=0
        )
        self.evento = Evento.objects.create(
            nome="Culto AP", data_inicio=base, data_fim=base + timedelta(hours=2)
        )
        self.voluntario = self._usuario("vol_ap")
        self.intruso = self._usuario("intruso_ap")
        self.lider = self._usuario("lider_ap")
        self.lider_outra = self._usuario("lider_outra_ap")
        Lideranca.objects.create(usuario=self.lider, equipe=self.equipe)
        Lideranca.objects.create(usuario=self.lider_outra, equipe=self.outra_equipe)

        self.escala = Escala.objects.create(
            usuario=self.voluntario, funcao=self.funcao, evento=self.evento,
            confirmada=True, data_confirmacao=timezone.now(),
        )
        self.desistencia = Desistencia.objects.create(
            escala=self.escala, usuario=self.voluntario, motivo="Viagem"
        )
        self.troca = SolicitacaoTroca.objects.create(
            escala_origem=self.escala, solicitante=self.voluntario,
            tipo_solicitacao="troca", data_solicitacao=timezone.now(),
        )

    def _usuario(self, username, **extra):
        user = criar_usuario(username)
        user.is_first_login = False
        user.termo_aceito_em = timezone.now()
        for campo, valor in extra.items():
            setattr(user, campo, valor)
        user.save()
        return user

    def _assert_nada_aprovado(self):
        self.desistencia.refresh_from_db()
        self.troca.refresh_from_db()
        self.escala.refresh_from_db()
        self.assertFalse(self.desistencia.aprovada)
        self.assertFalse(self.troca.aprovada)
        self.assertEqual(self.escala.usuario, self.voluntario)
        self.assertTrue(self.escala.confirmada)

    def _urls(self):
        return {
            'aprovar_desistencia': reverse('aprovar_desistencia', args=[self.desistencia.pk]),
            'aprovar_troca': reverse('aprovar_solicitacao_troca', args=[self.troca.pk]),
            'detalhes_desistencia': reverse('detalhes_desistencia_escala', args=[self.escala.pk]),
            'detalhes_troca': reverse('detalhes_solicitacao_troca', args=[self.troca.pk]),
        }

    def _assert_tudo_403(self, user):
        self.client.force_login(user)
        urls = self._urls()
        for nome in ('aprovar_desistencia', 'aprovar_troca'):
            resp = self.client.post(urls[nome])
            self.assertEqual(resp.status_code, 403, nome)
        for nome, url in urls.items():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, nome)
        self._assert_nada_aprovado()

    def test_voluntario_comum_recebe_403_e_nada_e_aprovado(self):
        self._assert_tudo_403(self.intruso)

    def test_lider_de_outra_equipe_recebe_403_e_nada_e_aprovado(self):
        self._assert_tudo_403(self.lider_outra)

    def test_anonimo_e_redirecionado_para_login(self):
        for nome, url in self._urls().items():
            resp = self.client.post(url)
            self.assertEqual(resp.status_code, 302, nome)
            self.assertIn('?next=', resp['Location'], nome)
        self._assert_nada_aprovado()

    def test_lider_da_equipe_ve_detalhes(self):
        self.client.force_login(self.lider)
        urls = self._urls()
        self.assertEqual(self.client.get(urls['detalhes_desistencia']).status_code, 200)
        self.assertEqual(self.client.get(urls['detalhes_troca']).status_code, 200)

    def test_lider_da_equipe_aprova_desistencia(self):
        self.client.force_login(self.lider)
        resp = self.client.post(self._urls()['aprovar_desistencia'])
        self.assertEqual(resp.status_code, 302)
        self.desistencia.refresh_from_db()
        self.escala.refresh_from_db()
        self.assertTrue(self.desistencia.aprovada)
        self.assertIsNone(self.escala.usuario)
        self.assertFalse(self.escala.confirmada)

    def test_lider_da_equipe_aprova_troca(self):
        self.client.force_login(self.lider)
        resp = self.client.post(self._urls()['aprovar_troca'])
        self.assertEqual(resp.status_code, 302)
        self.troca.refresh_from_db()
        self.escala.refresh_from_db()
        self.assertTrue(self.troca.aprovada)
        self.assertEqual(self.troca.lider_aprovador, self.lider)
        self.assertIsNone(self.escala.usuario)
        self.assertFalse(self.escala.confirmada)

    def test_aprovar_troca_por_get_nao_aprova(self):
        self.client.force_login(self.lider)
        resp = self.client.get(self._urls()['aprovar_troca'])
        self.assertEqual(resp.status_code, 302)
        self._assert_nada_aprovado()

    def test_reaprovar_troca_nao_limpa_escala_novamente(self):
        self.client.force_login(self.lider)
        url = self._urls()['aprovar_troca']
        self.client.post(url)
        self.escala.usuario = self.intruso  # vaga já foi repassada a outro voluntário
        self.escala.save()
        self.client.post(url)
        self.escala.refresh_from_db()
        self.assertEqual(self.escala.usuario, self.intruso)

    def test_staff_aprova_troca_sem_ser_lider(self):
        staff = self._usuario("staff_ap", is_staff=True)
        self.client.force_login(staff)
        resp = self.client.post(self._urls()['aprovar_troca'])
        self.assertEqual(resp.status_code, 302)
        self.troca.refresh_from_db()
        self.assertTrue(self.troca.aprovada)
