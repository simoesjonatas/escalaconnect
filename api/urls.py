from django.http import JsonResponse
from django.urls import path, re_path

from disponivel.services import disponibilidades
from ocupado.services import indisponibilidades

from .views import conta, devices, equipes, escalas, eventos, periodos
from .views.auth import LoginView, LogoutAllView, LogoutView
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
    path('auth/logout/', LogoutView.as_view(), name='api_logout'),
    path('auth/logout-all/', LogoutAllView.as_view(), name='api_logout_all'),

    path('me/', MeView.as_view(), name='api_me'),
    path('me/definir-senha/', conta.DefinirSenhaView.as_view(), name='api_definir_senha'),
    path('me/trocar-senha/', conta.TrocarSenhaView.as_view(), name='api_trocar_senha'),
    path('me/aceitar-termo/', conta.AceitarTermoView.as_view(), name='api_aceitar_termo'),
    path('termo/', conta.TermoView.as_view(), name='api_termo'),
    path('meta/', MetaView.as_view(), name='api_meta'),

    path('home/', escalas.HomeView.as_view(), name='api_home'),
    path('escalas/', escalas.EscalaListView.as_view(), name='api_escalas'),
    path('escalas/<int:pk>/', escalas.EscalaDetailView.as_view(), name='api_escala'),
    path('escalas/<int:pk>/confirmar/', escalas.ConfirmarEscalaView.as_view(), name='api_escala_confirmar'),
    path('escalas/<int:pk>/impedimento/', escalas.ImpedimentoView.as_view(), name='api_escala_impedimento'),
    path('escalas/<int:pk>/troca/', escalas.TrocaView.as_view(), name='api_escala_troca'),

    path('eventos/', eventos.EventoListView.as_view(), name='api_eventos'),
    *rotas_de_periodos('disponibilidades', disponibilidades),
    *rotas_de_periodos('indisponibilidades', indisponibilidades),

    path('equipes/', equipes.EquipeListView.as_view(), name='api_equipes'),
    path('equipes/<int:pk>/candidatura/', equipes.CandidaturaView.as_view(), name='api_candidatura'),

    path('devices/', devices.DeviceView.as_view(), name='api_devices'),
    path('devices/<str:token>/', devices.DeviceDetailView.as_view(), name='api_device'),

    re_path(r'^.*$', nao_encontrado),
]
