from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from .models import AtividadeDiaria, RegistroLogin, Usuario

LIMITE_ONLINE_MINUTOS = 5


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

    ultimos_logins = (
        RegistroLogin.objects
        .select_related('usuario')
        .order_by('-data_hora')[:10]
    )

    mais_ativos_30d = (
        AtividadeDiaria.objects
        .filter(data__gte=hoje - timedelta(days=29))
        .values('usuario__first_name', 'usuario__last_name', 'usuario__username')
        .annotate(dias=Count('id'))
        .order_by('-dias')[:10]
    )

    contexto = {
        'usuarios_online': usuarios_online,
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
        'ultimos_logins': ultimos_logins,
        'mais_ativos_30d': mais_ativos_30d,
        'limite_online_minutos': LIMITE_ONLINE_MINUTOS,
    }
    return render(request, 'usuario/monitoramento.html', contexto)
