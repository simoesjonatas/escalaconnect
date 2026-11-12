from django.http import JsonResponse
from django.urls import path, re_path

from disponivel.services import disponibilidades
from ocupado.services import indisponibilidades

from .views import (
    avisos, conta, devices, equipe_do_lider, equipes, escala_fixa, escalas, eventos, eventos_do_lider, lideranca,
    periodos,
)
from .views.auth import CadastroView, LoginView, LogoutAllView, LogoutView, RecuperarSenhaView
from .views.conta import MeView, MetaView


def rotas_de_periodos(prefixo, regras):
    """Rotas iguais para disponibilidades e indisponibilidades (ver escalaconnect/periodos.py)."""
    nome = f'api_{prefixo}'
    return [
        path(f'{prefixo}/', periodos.PeriodoListView.as_view(periodos=regras), name=nome),
        path(f'{prefixo}/eventos/', periodos.PeriodoEventosView.as_view(periodos=regras), name=f'{nome}_eventos'),
        path(f'{prefixo}/por-evento/', periodos.PeriodoPorEventoView.as_view(periodos=regras), name=f'{nome}_por_evento'),
        path(f'{prefixo}/<int:pk>/', periodos.PeriodoDetailView.as_view(periodos=regras), name=f'{nome}_detalhe'),
    ]


def nao_encontrado(request):
    # Sem isto, uma rota errada cairia no handler404 do site, que redireciona para "/".
    return JsonResponse({'code': 'not_found', 'detail': 'Rota não encontrada.'}, status=404)


urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='api_login'),
    path('auth/cadastro/', CadastroView.as_view(), name='api_cadastro'),
    path('auth/logout/', LogoutView.as_view(), name='api_logout'),
    path('auth/logout-all/', LogoutAllView.as_view(), name='api_logout_all'),
    path('auth/recuperar-senha/', RecuperarSenhaView.as_view(), name='api_recuperar_senha'),

    path('me/', MeView.as_view(), name='api_me'),
    path('me/definir-senha/', conta.DefinirSenhaView.as_view(), name='api_definir_senha'),
    path('me/trocar-senha/', conta.TrocarSenhaView.as_view(), name='api_trocar_senha'),
    path('me/aceitar-termo/', conta.AceitarTermoView.as_view(), name='api_aceitar_termo'),
    path('me/agenda/', conta.AgendaView.as_view(), name='api_agenda'),
    path('me/excluir-conta/', conta.ExcluirContaView.as_view(), name='api_excluir_conta'),
    path('me/historico/', escalas.HistoricoView.as_view(), name='api_historico'),
    path('termo/', conta.TermoView.as_view(), name='api_termo'),
    path('meta/', MetaView.as_view(), name='api_meta'),

    path('home/', escalas.HomeView.as_view(), name='api_home'),
    path('escalas/', escalas.EscalaListView.as_view(), name='api_escalas'),
    path('escalas/<int:pk>/', escalas.EscalaDetailView.as_view(), name='api_escala'),
    path('escalas/<int:pk>/confirmar/', escalas.ConfirmarEscalaView.as_view(), name='api_escala_confirmar'),
    path('escalas/<int:pk>/impedimento/', escalas.ImpedimentoView.as_view(), name='api_escala_impedimento'),
    path('escalas/<int:pk>/troca/', escalas.TrocaView.as_view(), name='api_escala_troca'),
    path('escalas/<int:pk>/equipe/', escalas.ColegasView.as_view(), name='api_escala_equipe'),
    path('avisos/', avisos.AvisoListView.as_view(), name='api_avisos'),
    path('avisos/ler/', avisos.LerAvisosView.as_view(), name='api_avisos_ler'),
    path('vagas/', escalas.VagaAbertaListView.as_view(), name='api_vagas'),
    path('vagas/<int:pk>/oferta/', escalas.OfertaView.as_view(), name='api_vaga_oferta'),

    path('eventos/', eventos.EventoListView.as_view(), name='api_eventos'),
    path('eventos/<int:pk>/escala/', eventos.EscalaDoEventoView.as_view(), name='api_evento_escala'),
    *rotas_de_periodos('disponibilidades', disponibilidades),
    *rotas_de_periodos('indisponibilidades', indisponibilidades),

    path('equipes/', equipes.EquipeListView.as_view(), name='api_equipes'),
    path('equipes/<int:pk>/candidatura/', equipes.CandidaturaView.as_view(), name='api_candidatura'),

    path('lider/pendencias/', lideranca.PendenciasView.as_view(), name='api_lider_pendencias'),
    re_path(r'^lider/impedimentos/(?P<pk>\d+)/(?P<acao>aprovar|recusar)/$',
            lideranca.ImpedimentoView.as_view(), name='api_lider_impedimento'),
    re_path(r'^lider/trocas/(?P<pk>\d+)/(?P<acao>aprovar|recusar)/$',
            lideranca.TrocaView.as_view(), name='api_lider_troca'),
    re_path(r'^lider/ofertas/(?P<pk>\d+)/(?P<acao>aprovar|recusar)/$',
            lideranca.OfertaView.as_view(), name='api_lider_oferta'),
    path('lider/cultos/', lideranca.CultoListView.as_view(), name='api_lider_cultos'),
    path('lider/cultos/<int:pk>/', lideranca.CultoDetailView.as_view(), name='api_lider_culto'),
    path('lider/cultos/<int:pk>/pedir-confirmacao/', lideranca.PedirConfirmacaoView.as_view(),
         name='api_lider_pedir_confirmacao'),
    path('lider/disponibilidade/', lideranca.DisponibilidadeDaEquipeView.as_view(), name='api_lider_disponibilidade'),
    path('lider/disponibilidade/pedir/', lideranca.PedirDisponibilidadeView.as_view(),
         name='api_lider_pedir_disponibilidade'),
    re_path(r'^lider/candidaturas/(?P<pk>\d+)/(?P<acao>aprovar|recusar)/$',
            lideranca.CandidaturaView.as_view(), name='api_lider_candidatura'),
    path('lider/vagas/', lideranca.VagaListView.as_view(), name='api_lider_vagas'),
    path('lider/eventos/', eventos_do_lider.EventosView.as_view(), name='api_lider_eventos'),
    path('lider/eventos/opcoes/', eventos_do_lider.OpcoesView.as_view(), name='api_lider_eventos_opcoes'),
    path('lider/eventos/em-massa/', eventos_do_lider.EventosEmMassaView.as_view(), name='api_lider_eventos_em_massa'),
    path('lider/eventos/funcoes/', eventos_do_lider.AplicarFuncoesView.as_view(), name='api_lider_eventos_funcoes'),
    path('lider/pdf/', eventos_do_lider.PdfDaEscalaView.as_view(), name='api_lider_pdf'),
    path('lider/equipes/<int:pk>/', equipe_do_lider.EquipeDoLiderView.as_view(), name='api_lider_equipe'),
    path('lider/equipes/<int:pk>/funcoes/', equipe_do_lider.FuncoesDaEquipeView.as_view(), name='api_lider_equipe_funcoes'),
    path('lider/equipes/<int:pk>/integrantes/', equipe_do_lider.IntegrantesView.as_view(),
         name='api_lider_equipe_integrantes'),
    path('lider/equipes/<int:pk>/escala-fixa/', escala_fixa.EscalaFixaView.as_view(), name='api_lider_escala_fixa'),
    path('lider/equipes/<int:pk>/escala-fixa/itens/', escala_fixa.ItensDaEscalaFixaView.as_view(),
         name='api_lider_escala_fixa_itens'),
    path('lider/escala-fixa/itens/<int:pk>/', escala_fixa.ItemDaEscalaFixaView.as_view(),
         name='api_lider_escala_fixa_item'),
    path('lider/funcoes/<int:pk>/', equipe_do_lider.FuncaoView.as_view(), name='api_lider_funcao'),
    path('lider/liderancas/<int:pk>/', equipe_do_lider.LiderancaView.as_view(), name='api_lider_lideranca'),
    path('lider/integrantes/<int:pk>/', equipe_do_lider.IntegranteView.as_view(), name='api_lider_integrante'),
    path('lider/vagas/<int:pk>/', lideranca.VagaDetailView.as_view(), name='api_lider_vaga'),
    path('lider/vagas/<int:pk>/escalar/', lideranca.EscalarView.as_view(), name='api_lider_escalar'),
    path('lider/pessoas/<int:pk>/escolhas/', lideranca.EscolhasDaPessoaView.as_view(),
         name='api_lider_escolhas_da_pessoa'),

    path('devices/', devices.DeviceView.as_view(), name='api_devices'),
    path('devices/<str:token>/', devices.DeviceDetailView.as_view(), name='api_device'),

    re_path(r'^.*$', nao_encontrado),
]
