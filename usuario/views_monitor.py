from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from .models import AtividadeDiaria, RegistroLogin, Usuario

LIMITE_ONLINE_MINUTOS = 5
POR_PAGINA = 15
LIMITE_LISTA = 10  # "Online agora" e "Mais ativos" mostram só os primeiros

PERIODOS = [('hoje', 'Hoje'), ('7', '7 dias'), ('30', '30 dias'), ('todos', 'Tudo')]


def _desde(periodo):
    """Início do período escolhido nos filtros (None = sem limite)."""
    hoje = timezone.localdate()
    if periodo == 'hoje':
        return hoje
    if periodo in ('7', '30'):
        return hoje - timedelta(days=int(periodo) - 1)
    return None


def _busca_por_nome(busca, prefixo=''):
    """Filtro por nome, sobrenome ou usuário (prefixo = caminho até o usuário, ex.: 'usuario__')."""
    filtro = Q()
    for termo in busca.split():
        filtro &= (
            Q(**{f'{prefixo}first_name__icontains': termo})
            | Q(**{f'{prefixo}last_name__icontains': termo})
            | Q(**{f'{prefixo}username__icontains': termo})
        )
    return filtro


def _pagina(request, itens):
    return Paginator(itens, POR_PAGINA).get_page(request.GET.get('page'))


@login_required
def monitoramento_uso(request):
    if not request.user.is_superuser:
        return render(request, '403_forbidden.html', status=403)

    agora = timezone.now()
    hoje = timezone.localdate()
    limite_online = agora - timedelta(minutes=LIMITE_ONLINE_MINUTOS)

    # Sessões não expiradas e usuários únicos com sessão aberta
    sessoes_ativas = 0
    usuarios_com_sessao = set()
    for sessao in Session.objects.filter(expire_date__gte=agora):
        sessoes_ativas += 1
        uid = sessao.get_decoded().get('_auth_user_id')
        if uid:
            usuarios_com_sessao.add(uid)

    usuarios_online = list(
        Usuario.objects
        .filter(ultima_atividade__gte=limite_online)
        .order_by('-ultima_atividade')
    )

    total_usuarios = Usuario.objects.count()
    ja_usaram = Usuario.objects.filter(last_login__isnull=False).count()

    ativos_hoje = AtividadeDiaria.objects.filter(data=hoje).count()
    ativos_7d = (
        AtividadeDiaria.objects
        .filter(data__gte=hoje - timedelta(days=6))
        .values('usuario').distinct().count()
    )
    ativos_30d = (
        AtividadeDiaria.objects
        .filter(data__gte=hoje - timedelta(days=29))
        .values('usuario').distinct().count()
    )

    # Logins por dia para o gráfico (últimos 14 dias)
    inicio_grafico = hoje - timedelta(days=13)
    logins_por_dia = dict(
        RegistroLogin.objects
        .filter(data_hora__gte=agora - timedelta(days=14))
        .annotate(dia=TruncDate('data_hora'))
        .values('dia')
        .annotate(qtd=Count('id'))
        .values_list('dia', 'qtd')
    )
    maximo = max(logins_por_dia.values(), default=0) or 1
    grafico_logins = []
    for indice in range(14):
        dia = inicio_grafico + timedelta(days=indice)
        qtd = logins_por_dia.get(dia, 0)
        grafico_logins.append({
            'dia': dia,
            'qtd': qtd,
            'altura': round(qtd * 100 / maximo),
        })

    # Histórico de acessos com filtro de período e nome, paginado.
    periodo = request.GET.get('periodo') or '7'
    busca = (request.GET.get('q') or '').strip()
    acessos = RegistroLogin.objects.select_related('usuario').order_by('-data_hora')
    desde = _desde(periodo)
    if desde:
        acessos = acessos.filter(data_hora__date__gte=desde)
    if busca:
        acessos = acessos.filter(_busca_por_nome(busca, 'usuario__'))

    mais_ativos_30d = (
        AtividadeDiaria.objects
        .filter(data__gte=hoje - timedelta(days=29))
        .values('usuario__first_name', 'usuario__last_name', 'usuario__username')
        .annotate(dias=Count('id'))
        .order_by('-dias')[:LIMITE_LISTA]
    )

    contexto = {
        'usuarios_online': usuarios_online[:LIMITE_LISTA],
        'online_alem_da_lista': max(len(usuarios_online) - LIMITE_LISTA, 0),
        'qtd_online': len(usuarios_online),
        'sessoes_ativas': sessoes_ativas,
        'usuarios_com_sessao': len(usuarios_com_sessao),
        'total_usuarios': total_usuarios,
        'ja_usaram': ja_usaram,
        'nunca_usaram': total_usuarios - ja_usaram,
        'novos_30d': Usuario.objects.filter(date_joined__gte=agora - timedelta(days=30)).count(),
        'ativos_hoje': ativos_hoje,
        'ativos_7d': ativos_7d,
        'ativos_30d': ativos_30d,
        'grafico_logins': grafico_logins,
        'page_obj': _pagina(request, acessos),
        'acessos_pessoas': acessos.values('usuario').distinct().count(),
        'periodos': PERIODOS,
        'periodo': periodo,
        'busca': busca,
        'mais_ativos_30d': mais_ativos_30d,
        'limite_online_minutos': LIMITE_ONLINE_MINUTOS,
    }
    return render(request, 'usuario/monitoramento.html', contexto)


@login_required
def monitoramento_app(request):
    """Quem usa o aplicativo: aparelhos registrados e sessões (tokens) válidas, com filtros."""
    if not request.user.is_superuser:
        return render(request, '403_forbidden.html', status=403)

    from api.models import Device
    from knox.models import AuthToken
    from knox.settings import knox_settings

    agora = timezone.now()
    hoje = timezone.localdate()
    ttl = knox_settings.TOKEN_TTL

    aba = 'sessoes' if request.GET.get('aba') == 'sessoes' else 'aparelhos'
    busca = (request.GET.get('q') or '').strip()
    periodo = request.GET.get('periodo') or 'todos'
    plataforma = request.GET.get('plataforma') or ''
    push = request.GET.get('push') or ''
    desde = _desde(periodo)

    todos_aparelhos = Device.objects.all()
    aparelhos = Device.objects.select_related('usuario').order_by('-ultimo_uso')
    if busca:
        aparelhos = aparelhos.filter(_busca_por_nome(busca, 'usuario__'))
    if plataforma in ('android', 'ios'):
        aparelhos = aparelhos.filter(plataforma=plataforma)
    if push in ('ativo', 'desligado'):
        aparelhos = aparelhos.filter(ativo=(push == 'ativo'))
    if desde:
        aparelhos = aparelhos.filter(ultimo_uso__date__gte=desde)

    # Sessões do app por usuário. O knox renova a validade a cada uso (no máximo
    # 1x por hora), então "validade - TTL" é o último uso aproximado da sessão.
    tokens = AuthToken.objects.filter(expiry__gt=agora).select_related('user').order_by('-expiry')
    sessoes = {}
    for token in tokens:
        info = sessoes.setdefault(token.user, {'usuario': token.user, 'qtd': 0, 'primeiro_login': token.created, 'ultimo_uso': None})
        info['qtd'] += 1
        info['primeiro_login'] = min(info['primeiro_login'], token.created)
        ultimo_uso = token.expiry - ttl
        if info['ultimo_uso'] is None or ultimo_uso > info['ultimo_uso']:
            info['ultimo_uso'] = ultimo_uso
    sessoes = sorted(sessoes.values(), key=lambda s: s['ultimo_uso'], reverse=True)
    usaram_hoje = sum(1 for s in sessoes if timezone.localdate(s['ultimo_uso']) == hoje)
    total_sessoes = len(sessoes)
    if busca:
        ids = set(Usuario.objects.filter(_busca_por_nome(busca)).values_list('pk', flat=True))
        sessoes = [s for s in sessoes if s['usuario'].pk in ids]
    if desde:
        sessoes = [s for s in sessoes if timezone.localdate(s['ultimo_uso']) >= desde]

    lista = aparelhos if aba == 'aparelhos' else sessoes
    contexto = {
        'aba': aba,
        'page_obj': _pagina(request, lista),
        'total_filtrado': aparelhos.count() if aba == 'aparelhos' else len(sessoes),
        'busca': busca,
        'periodo': periodo,
        'plataforma': plataforma,
        'push': push,
        'periodos': PERIODOS,
        'usuarios_com_app': total_sessoes,
        'aparelhos_ativos': todos_aparelhos.filter(ativo=True).count(),
        'aparelhos_total': todos_aparelhos.count(),
        'android': todos_aparelhos.filter(ativo=True, plataforma='android').count(),
        'ios': todos_aparelhos.filter(ativo=True, plataforma='ios').count(),
        'usaram_hoje': usaram_hoje,
        'total_usuarios': Usuario.objects.count(),
        'validade_dias': ttl.days,
    }
    return render(request, 'usuario/monitoramento_app.html', contexto)
