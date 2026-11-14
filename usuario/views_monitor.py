from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.utils.timesince import timesince

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


SEM_VERSAO = 'sem'


def _chave_de_versao(versao):
    """'1.10.0' depois de '1.9.2': compara número a número; sem versão vai para o fim."""
    try:
        return (1, tuple(int(parte) for parte in versao.split('.')))
    except ValueError:
        return (0, ())


def _versoes(aparelhos):
    """Versões do app nos aparelhos com push ativo (o app informa a versão a cada abertura),
    da mais nova para a mais antiga, com quantos aparelhos em cada."""
    contagem = (aparelhos.filter(ativo=True).values('app_versao').annotate(n=Count('id')).order_by())
    versoes = [
        {'valor': c['app_versao'] or SEM_VERSAO, 'rotulo': c['app_versao'] or 'sem versão', 'n': c['n']}
        for c in contagem
    ]
    return sorted(versoes, key=lambda v: _chave_de_versao(v['rotulo']), reverse=True)


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
    versao = request.GET.get('versao') or ''
    desde = _desde(periodo)

    todos_aparelhos = Device.objects.all()
    aparelhos = Device.objects.select_related('usuario').order_by('-ultimo_uso')
    if busca:
        aparelhos = aparelhos.filter(_busca_por_nome(busca, 'usuario__'))
    if plataforma in ('android', 'ios'):
        aparelhos = aparelhos.filter(plataforma=plataforma)
    if push in ('ativo', 'desligado'):
        aparelhos = aparelhos.filter(ativo=(push == 'ativo'))
    if versao:
        aparelhos = aparelhos.filter(app_versao='' if versao == SEM_VERSAO else versao)
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
        'versao': versao,
        'versoes': _versoes(todos_aparelhos),
        'sem_versao': SEM_VERSAO,
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


STATUS_PUSH = [('', 'Todos'), ('sent', 'Enviados'), ('error', 'Com erro'), ('skipped', 'Pulados')]


@login_required
def monitoramento_fila(request):
    """Fila e push: o Celery está de pé? O que está na fila, o que o beat agenda e os últimos pushes."""
    if not request.user.is_superuser:
        return render(request, '403_forbidden.html', status=403)

    from escalaconnect import monitor_fila
    from evento.models import Notification, NotificationAttempt

    agora = timezone.now()
    # Publica um batimento de teste (no máx. 1 a cada 30 s): confirma que a fila aceita tarefas.
    # Não manda e-mail: quem está olhando a página já está vendo.
    estado = monitor_fila.estado(publicar=True)

    def ha(momento):
        """'agora mesmo' / 'há 3 minutos' (None se nunca)."""
        if momento is None:
            return None
        return 'agora mesmo' if agora - momento < timedelta(minutes=1) else f'há {timesince(momento, agora)}'

    def segundos_atras(segundos):
        return None if segundos is None else agora - timedelta(seconds=segundos)

    tentativas = NotificationAttempt.objects.filter(notification__channel=Notification.CHANNEL_PUSH)
    ultimas_24h = dict(
        tentativas.filter(created_at__gte=agora - timedelta(hours=24))
        .values_list('status').annotate(n=Count('id')).order_by()
    )
    ultimo_enviado = tentativas.filter(status='sent').order_by('-created_at').values_list('created_at', flat=True).first()

    status = request.GET.get('status') or ''
    if status not in dict(STATUS_PUSH):
        status = ''
    lista = tentativas.select_related('notification__usuario').order_by('-created_at')
    if status:
        lista = lista.filter(status=status)

    broker = monitor_fila.fila_no_broker()
    # Com o broker fora não adianta perguntar ao worker (seria só mais espera).
    worker = monitor_fila.tarefas_no_worker() if broker['erro'] is None else None
    problemas = list(estado['problemas'])
    codigos = {p.codigo for p in problemas}
    if broker['erro'] is None and worker is None and 'worker_parado' not in codigos:
        # Pergunta direta, mais rápida que esperar o batimento envelhecer: o processo principal do
        # worker responde mesmo com todas as tarefas ocupadas.
        problemas.append(monitor_fila.Problema(
            'worker_parado', 'O worker não respondeu agora (1 s de espera). Se a fila só cresce, ele está parado.'))
    contexto = {
        'problemas': problemas,
        'batimento': estado['batimento'],
        'fila_aceita': estado.get('fila_aceita'),
        'ultimo_worker': ha(segundos_atras(estado.get('worker_seg'))),
        'ultimo_beat': ha(segundos_atras(estado.get('beat_seg'))),
        'limite_minutos': settings.MONITOR_FILA_MINUTOS,
        'broker': broker,
        'worker': worker,
        'agenda': monitor_fila.agenda_do_beat(),
        'enviados_24h': ultimas_24h.get('sent', 0),
        'erros_24h': ultimas_24h.get('error', 0),
        'pulados_24h': ultimas_24h.get('skipped', 0),
        'ultimo_enviado': ultimo_enviado,
        'ultimo_enviado_ha': ha(ultimo_enviado),
        'page_obj': _pagina(request, lista),
        'status': status,
        'status_push': STATUS_PUSH,
    }
    return render(request, 'usuario/monitoramento_fila.html', contexto)
