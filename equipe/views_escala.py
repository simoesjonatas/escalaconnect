from django.shortcuts import render, get_object_or_404
from .models import Equipe, Lideranca
from escala.models import Escala, Desistencia, Funcao
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from ocupado.models import Ocupado
from disponivel.models import Disponivel
from equipe.decorators import require_lideranca
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.datastructures import MultiValueDictKeyError
from django.conf import settings
from datetime import datetime

from escalaconnect.tasks_availability import disparar_pedido_disponibilidades
from escala.utils import preencher_vagas, usuarios_disponiveis_para_evento, LIMITE_ESCALAS_POR_MES

VISOES_ESCALA = ('lista', 'grade')
COOKIE_VISAO_ESCALA = 'connect-escalas-view'

def get_unapproved_desistencias(equipe_id):
    equipe = get_object_or_404(Equipe, pk=equipe_id)
    
    # Realiza a consulta para obter desistências não aprovadas
    desistencias = Desistencia.objects.filter(
        escala__funcao__equipe=equipe, 
        aprovada=False
    )
    
    return desistencias

@require_lideranca
def listar_escalas(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)

    # Visão escolhida: a da URL vence; sem ela, vale a última usada (cookie).
    visao = request.GET.get('view')
    if visao not in VISOES_ESCALA:
        visao = request.COOKIES.get(COOKIE_VISAO_ESCALA)
    if visao not in VISOES_ESCALA:
        visao = 'lista'

    if visao == 'grade':
        response = render(request, 'equipe/escalas_equipe.html', _contexto_grade(request, equipe))
        response.set_cookie(COOKIE_VISAO_ESCALA, visao, max_age=60 * 60 * 24 * 365, samesite='Lax')
        return response

    order_by = request.GET.get('order_by', 'evento__data_inicio')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')
    
    if direction == 'desc':
        order_by = f'-{order_by}'

    # Filter escalas from today onwards
    # current_date = timezone.now()
    today = timezone.now().date()
    escalas_list = (Escala.objects
        .filter(funcao__equipe=equipe, evento__data_inicio__date__gte=today)
        .select_related('funcao', 'funcao__equipe', 'evento', 'usuario')
        .order_by(order_by)
    )
    if query:
        escalas_list = escalas_list.filter(
            Q(evento__nome__icontains=query) | 
            Q(funcao__nome__icontains=query) |
            Q(usuario__username__icontains=query) |
            Q(funcao__equipe__nome__icontains=query)
        ).order_by(order_by)

    paginator = Paginator(escalas_list, 10)  # Display 10 escalas per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # desistencias =get_unapproved_desistencias(equipe.pk)

    response = render(request, 'equipe/escalas_equipe.html', {
        'equipe': equipe,
        'visao': visao,
        'page_obj': page_obj,
        'order_by': order_by.strip('-'),
        'direction': direction,
        'query': query,
        # 'desistencias': desistencias,
        'escala_fields': [
            ('evento__nome', 'Evento'),
            ('evento__data_inicio', 'Data Início'),
            ('funcao__nome', 'Função'),
            ('__disponiveis__', 'Disp.'),
            ('usuario__username', 'Usuário'),
            ('confirmada', 'Confirmada'),
        ]
    })
    response.set_cookie(COOKIE_VISAO_ESCALA, visao, max_age=60 * 60 * 24 * 365, samesite='Lax')
    return response


def _contexto_grade(request, equipe):
    """Monta a grade mensal: uma linha por evento, uma coluna por função."""
    hoje = timezone.localdate()
    try:
        mes_ref = datetime.strptime(request.GET.get('mes', ''), '%Y-%m').date()
    except ValueError:
        mes_ref = hoje.replace(day=1)

    def _virar_mes(data, delta):
        indice = data.year * 12 + (data.month - 1) + delta
        return data.replace(year=indice // 12, month=indice % 12 + 1, day=1)

    mes_anterior = _virar_mes(mes_ref, -1)
    mes_seguinte = _virar_mes(mes_ref, 1)
    inicio = timezone.make_aware(datetime(mes_ref.year, mes_ref.month, 1))
    fim = timezone.make_aware(datetime(mes_seguinte.year, mes_seguinte.month, 1))

    funcoes = list(Funcao.objects.filter(equipe=equipe).order_by('nome'))
    coluna_por_funcao = {funcao.id: i for i, funcao in enumerate(funcoes)}

    escalas = (Escala.objects
        .filter(funcao__equipe=equipe, evento__data_inicio__gte=inicio, evento__data_inicio__lt=fim)
        .select_related('funcao', 'evento', 'usuario')
        .order_by('evento__data_inicio', 'evento_id', 'funcao__nome', 'pk')
    )

    linhas = []
    linha_por_evento = {}
    total = preenchidas = 0
    for escala in escalas:
        linha = linha_por_evento.get(escala.evento_id)
        if linha is None:
            linha = {
                'evento': escala.evento,
                'passado': timezone.localtime(escala.evento.data_inicio).date() < hoje,
                'celulas': [[] for _ in funcoes],
                'disponiveis': None,
            }
            linha_por_evento[escala.evento_id] = linha
            linhas.append(linha)

        total += 1
        if escala.usuario_id:
            preenchidas += 1
        elif not linha['passado']:
            # Vaga em aberto: quantos da equipe ainda podem assumir (uma conta por evento).
            if linha['disponiveis'] is None:
                linha['disponiveis'] = len(usuarios_disponiveis_para_evento(equipe, escala.evento))
            escala.vaga_disponiveis = linha['disponiveis']
        linha['celulas'][coluna_por_funcao[escala.funcao_id]].append(escala)

    return {
        'equipe': equipe,
        'visao': 'grade',
        'query': '',
        'mes_ref': mes_ref,
        'mes_anterior': mes_anterior,
        'mes_seguinte': mes_seguinte,
        'mes_atual': hoje.replace(day=1),
        'funcoes': funcoes,
        'linhas': linhas,
        'total_vagas': total,
        'vagas_preenchidas': preenchidas,
        'vagas_abertas': total - preenchidas,
    }


def escala_detail_equipe(request, equipe_pk, pk):
    escala = get_object_or_404(Escala, pk=pk)
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    evento_inicio = escala.evento.data_inicio
    evento_fim = escala.evento.data_fim
    evento = escala.evento
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()

    # membros aprovados da equipe (assumindo que há FK 'usuario' no modelo de membro)
    membros_qs = (
        escala.funcao.equipe.membros
        .filter(aprovado=True)
        .select_related('usuario')
    )

    # >>> ADIÇÃO: lista dos usuários da equipe para o modal <<<
    usuarios_equipe = [m.usuario for m in membros_qs if m.usuario is not None]
    usuarios_equipe.sort(key=lambda u: (u.get_full_name() or u.username).lower())

    # Usuários sem indisponibilidade
    usuarios_sem_indisponibilidade = [
        membro.usuario for membro in membros_qs
        if not Ocupado.objects.filter(
            usuario=membro.usuario,
            data_inicio__lt=evento_fim,
            data_fim__gt=evento_inicio
        ).exists()
    ]

    # Usuários com disponibilidade para o evento
    usuarios_com_disponibilidade = [
        usuario for usuario in usuarios_sem_indisponibilidade
        if Disponivel.objects.filter(
            usuario=usuario,
            data_inicio__lte=evento_inicio,
            data_fim__gte=evento_fim
        ).exists()
    ]

    # Usuários já escalados para o evento
    usuarios_ja_escalados = list(
        Escala.objects
        .filter(usuario__in=usuarios_sem_indisponibilidade, evento=evento)
        .exclude(pk=escala.pk)
        .select_related('funcao', 'funcao__equipe', 'usuario')
    )

    # Usuários disponíveis e não escalados
    usuarios_disponiveis = [
        usuario for usuario in usuarios_com_disponibilidade
        if not Escala.objects.filter(usuario=usuario, evento=evento).exclude(pk=escala.pk).exists()
    ]

    # Quantas vezes cada pessoa (disponível OU já escalada no evento) já foi
    # escalada NESTE mês NESTA equipe — dá ao líder a base para equilibrar quem
    # já serviu bastante. Usa o mês no fuso local (mesma contagem do auto-escalar);
    # uma query só, anexada em cada usuário.
    mes_evento = timezone.localtime(evento.data_inicio)
    ids_relevantes = {u.id for u in usuarios_disponiveis}
    ids_relevantes.update(e.usuario_id for e in usuarios_ja_escalados)
    servicos_no_mes = dict(
        Escala.objects
        .filter(
            funcao__equipe=equipe,
            usuario_id__in=ids_relevantes,
            evento__data_inicio__year=mes_evento.year,
            evento__data_inicio__month=mes_evento.month,
        )
        .values('usuario_id')
        .annotate(total=Count('id'))
        .values_list('usuario_id', 'total')
    )
    for usuario in usuarios_disponiveis:
        usuario.servicos_no_mes = servicos_no_mes.get(usuario.id, 0)
    for esc in usuarios_ja_escalados:
        esc.usuario.servicos_no_mes = servicos_no_mes.get(esc.usuario_id, 0)

    return render(request, 'equipe/equipe_escala_detail.html', {
        'escala': escala,
        'equipe': equipe,
        'usuarios_disponiveis': usuarios_disponiveis,
        'usuarios_escalados': usuarios_ja_escalados,
        'usuarios_equipe': usuarios_equipe,  # <<< AQUI
        'is_leader': is_leader,
        'limite_escalas_mes': getattr(settings, 'ESCALA_LIMITE_POR_MES', LIMITE_ESCALAS_POR_MES),
    })

@require_lideranca
def lider_pedir_disponibilidades(request, equipe_id: int):
    if request.method != "POST":
        return redirect("disponibilidades_equipe", equipe_pk=equipe_id)

    try:
        ano = int(request.POST["ano"])
        mes = int(request.POST["mes"])
    except (MultiValueDictKeyError, ValueError):
        messages.error(request, "Informe um mês e ano válidos.")
        return redirect("disponibilidades_equipe", equipe_pk=equipe_id)

    lider_nome = request.user.get_full_name() or request.user.get_username()
    # Botão "Lembrar só pelo app" manda canal=app; o outro manda e-mail e app.
    so_app = request.POST.get("canal") == "app"
    canais = ["push"] if so_app else ["email", "push"]

    # publica no worker: só enviará para quem AINDA NÃO cadastrou no mês
    task_result = disparar_pedido_disponibilidades.delay(
        ano=ano,
        mes=mes,
        equipe_id=equipe_id,
        lider_nome=lider_nome,
        canais=canais,
    )

    por_onde = "pelo app" if so_app else "por e-mail e pelo app"
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        resultado = task_result.get()
        resultado = resultado if isinstance(resultado, dict) else {}
        partes = [f"{resultado.get('push_enfileirados', 0)} notificação(ões) no app"]
        if not so_app:
            partes.insert(0, f"{resultado.get('emails_enviados', 0)} e-mail(s)")
        messages.success(
            request,
            f"Lembretes processados para {mes:02d}/{ano}: {' e '.join(partes)}, "
            f"{resultado.get('usuarios_faltantes', 0)} pendente(s)."
        )
    else:
        messages.success(
            request,
            f"Lembretes enviados {por_onde} para {mes:02d}/{ano}, só a quem ainda não informou disponibilidade."
        )
    return redirect("disponibilidades_equipe", equipe_pk=equipe_id)


@require_lideranca
def auto_escalar_equipe(request, equipe_pk):
    """Preenche automaticamente as vagas futuras em aberto desta equipe.

    Mesmo critério da auto-escala por evento (rodízio justo), mas para todos os
    eventos futuros da equipe de uma vez.
    """
    equipe = get_object_or_404(Equipe, pk=equipe_pk)

    if request.method != 'POST':
        return redirect('listar_escalas', equipe_pk=equipe_pk)

    hoje = timezone.now().date()
    vagas = list(
        Escala.objects
        .filter(
            funcao__equipe=equipe,
            usuario__isnull=True,
            evento__data_inicio__date__gte=hoje,
        )
        .select_related('funcao', 'funcao__equipe', 'evento')
        .order_by('evento__data_inicio')
    )
    preenchidas = preencher_vagas(vagas)

    if not vagas:
        messages.info(request, "Não há vagas em aberto nesta equipe.")
    else:
        if preenchidas:
            messages.success(request, f"{preenchidas} vaga(s) preenchida(s) automaticamente.")
        restantes = len(vagas) - preenchidas
        if restantes:
            messages.warning(request, f"{restantes} vaga(s) sem voluntário disponível no momento.")

    return redirect('listar_escalas', equipe_pk=equipe_pk)
