import calendar
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala.models import Escala, Desistencia, SolicitacaoTroca
from escala.utils import usuarios_disponiveis_para_evento
from django.utils.timezone import now, localtime
from equipe.lideranca_forms import LiderancaForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from escalaconnect.utils import admin_required
from equipe.decorators import require_lideranca  # Importando o decorador personalizado

User = get_user_model()


def verificar_permissao_lideranca(request, equipe):
    """
    Verifica se o usuário tem permissão para gerenciar lideranças.
    Apenas um líder da equipe, um superusuário ou um usuário staff pode adicionar, editar ou excluir líderes.
    """
    if not (request.user.is_superuser or request.user.is_staff or 
            Lideranca.objects.filter(usuario=request.user, equipe=equipe).exists()):
        raise PermissionDenied("Você não tem permissão para gerenciar lideranças desta equipe.")


def lideranca_list(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    
    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'
    
    liderancas = equipe.lideranca_set.filter(
        Q(usuario__username__icontains=query)
    ).order_by(order_by)
    
    paginator = Paginator(liderancas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    lideranca_fields = [
        ('id', 'ID'),
        ('usuario', 'Líder'),
    ]

    context = {
        'equipe': equipe,
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'lideranca_fields': lideranca_fields,
        'query': query
    }
    return render(request, 'lideranca/lideranca_list.html', context)

@require_lideranca
def lideranca_detail(request, pk):
    lideranca = get_object_or_404(Lideranca, pk=pk)
    return render(request, 'lideranca/lideranca_detail.html', {'lideranca': lideranca})

@require_lideranca
@admin_required
def lideranca_create(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    
    # Verifica se o usuário tem permissão
    verificar_permissao_lideranca(request, equipe)
    
    if request.method == 'POST':
        form = LiderancaForm(request.POST, equipe=equipe)
        if form.is_valid():
            lideranca = form.save(commit=False)
            lideranca.equipe = equipe
            lideranca.save()

            # Verifica se o usuário já é membro, se não, adiciona automaticamente
            if not MembrosEquipe.objects.filter(usuario=lideranca.usuario, equipe=equipe).exists():
                MembrosEquipe.objects.create(usuario=lideranca.usuario, equipe=equipe)

            return redirect(reverse('listar_liderancas', args=[equipe_pk]))
    else:
        form = LiderancaForm(equipe=equipe)
    
    return render(request, 'lideranca/lideranca_form.html', {'form': form, 'equipe': equipe})

@login_required
@require_lideranca
def lideranca_update(request, pk):
    lideranca = get_object_or_404(Lideranca, pk=pk)
    
    # Verifica se o usuário tem permissão
    verificar_permissao_lideranca(request, lideranca.equipe)

    
    if request.method == 'POST':
        form = LiderancaForm(request.POST, instance=lideranca)
        if form.is_valid():
            lideranca = form.save()

            # Verifica se o usuário já é membro, se não, adiciona automaticamente
            if not MembrosEquipe.objects.filter(usuario=lideranca.usuario, equipe=lideranca.equipe).exists():
                MembrosEquipe.objects.create(usuario=lideranca.usuario, equipe=lideranca.equipe)

            return redirect('listar_liderancas', equipe_pk=lideranca.equipe.pk)
    else:
        form = LiderancaForm(instance=lideranca)
    
    return render(request, 'lideranca/lideranca_form.html', {'form': form, 'lideranca': lideranca, 'equipe': lideranca.equipe})

@login_required
@require_lideranca
def lideranca_delete(request, pk):
    lideranca = get_object_or_404(Lideranca, pk=pk)
    
    # Verifica se o usuário tem permissão
    verificar_permissao_lideranca(request, lideranca.equipe)
    
    if request.method == 'POST':
        lideranca.delete()
        return redirect('listar_liderancas', equipe_pk=lideranca.equipe.pk)

    return render(request, 'lideranca/lideranca_confirm_delete.html', {'lideranca': lideranca})


@login_required
def dashboard_lider(request):
    """Painel do líder: buracos na escala, taxa de confirmação e ranking de participação.

    Considera as equipes que o usuário lidera (todas, se for staff/superuser).
    """
    if request.user.is_superuser or request.user.is_staff:
        equipes = list(Equipe.objects.all())
    else:
        equipes = list(Equipe.objects.filter(lideranca__usuario=request.user).distinct())

    escalas = Escala.objects.filter(funcao__equipe__in=equipes)
    futuras = escalas.filter(evento__data_inicio__gte=now())

    designadas_total = futuras.filter(usuario__isnull=False).count()
    confirmadas = futuras.filter(usuario__isnull=False, confirmada=True).count()

    buracos = (
        futuras.filter(usuario__isnull=True)
        .select_related('evento', 'funcao', 'funcao__equipe')
        .order_by('evento__data_inicio')
    )

    ranking = (
        escalas.filter(usuario__isnull=False)
        .values('usuario__first_name', 'usuario__last_name', 'usuario__username')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )

    # Pendências que travam a escala: desistências e trocas aguardando o líder.
    # Só de eventos de hoje para frente (pendência de evento passado não interessa mais).
    agora = now()
    impedimentos = (
        Desistencia.objects
        .filter(
            escala__funcao__equipe__in=equipes,
            aprovada=False,
            escala__evento__data_inicio__gte=agora,
        )
        .select_related('escala', 'escala__evento', 'escala__funcao', 'escala__funcao__equipe', 'usuario')
        .order_by('escala__evento__data_inicio')
    )
    trocas_abertas = (
        SolicitacaoTroca.objects
        .filter(
            escala_origem__funcao__equipe__in=equipes,
            aprovada=False,
            escala_origem__evento__data_inicio__gte=agora,
        )
        .select_related(
            'escala_origem', 'escala_origem__evento',
            'escala_origem__funcao', 'escala_origem__funcao__equipe', 'solicitante',
        )
        .order_by('escala_origem__evento__data_inicio')
    )

    # Voluntários que ainda dá para aproveitar: membros aprovados que NÃO foram
    # escalados na equipe neste mês E que conseguem cobrir alguma OPORTUNIDADE
    # futura da equipe — seja uma vaga em aberto, seja uma escala ainda NÃO
    # CONFIRMADA ocupada por quem já atuou no mês (dá para passar a vez a quem
    # ainda não serviu). Basear na oportunidade futura (e não em "tem
    # disponibilidade no mês") evita apontar quem só se disponibilizou para datas
    # passadas ou quem está numa equipe sem nada em aberto daqui em diante.
    agora_local = localtime(now())
    inicio_mes = agora_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ultimo_dia = calendar.monthrange(agora_local.year, agora_local.month)[1]
    fim_mes = agora_local.replace(
        day=ultimo_dia, hour=23, minute=59, second=59, microsecond=999999
    )
    # Horizonte para procurar vagas (alinhado ao período de disponibilidade).
    horizonte = agora_local + timedelta(days=60)

    disponiveis_ociosos = []
    ociosos_total = 0
    alguem_escalado_no_mes = False
    for equipe in equipes:
        membros_ids = list(
            MembrosEquipe.objects
            .filter(equipe=equipe, aprovado=True)
            .values_list('usuario_id', flat=True)
        )
        if not membros_ids:
            continue
        # Quem já foi escalado na equipe em algum evento deste mês.
        ja_escalados = set(
            Escala.objects
            .filter(
                funcao__equipe=equipe,
                usuario_id__in=membros_ids,
                evento__data_inicio__gte=inicio_mes,
                evento__data_inicio__lte=fim_mes,
            )
            .values_list('usuario_id', flat=True)
        )
        if ja_escalados:
            alguem_escalado_no_mes = True
        candidatos = set(membros_ids) - ja_escalados
        if not candidatos:
            continue

        # Oportunidades futuras da equipe: vagas em aberto OU escalas ainda não
        # confirmadas ocupadas por quem já atuou neste mês. Escala confirmada
        # nunca entra (não sugerimos desfazer algo que a pessoa já confirmou).
        oportunidades = list(
            Escala.objects
            .filter(
                funcao__equipe=equipe,
                confirmada=False,
                evento__data_inicio__gte=agora_local,
                evento__data_inicio__lte=horizonte,
            )
            .filter(Q(usuario__isnull=True) | Q(usuario_id__in=ja_escalados))
            .select_related('evento', 'funcao', 'usuario')
            .order_by('evento__data_inicio')
        )
        if not oportunidades:
            continue

        # Para cada candidato, a próxima oportunidade que ele cobre (disponível no
        # horário, sem conflito). Preenchemos primeiro as vagas VAZIAS (menos
        # disruptivo) e só então sugerimos a troca com quem já serviu. As duas
        # listas já vêm ordenadas por data. Quem não cobre nada não entra.
        vazias = [o for o in oportunidades if o.usuario_id is None]
        trocas = [o for o in oportunidades if o.usuario_id is not None]
        proxima_vaga = {}
        disp_cache = {}
        for lista in (vazias, trocas):
            for opp in lista:
                if len(proxima_vaga) == len(candidatos):
                    break
                ev = opp.evento
                if ev.id not in disp_cache:
                    disp_cache[ev.id] = set(usuarios_disponiveis_para_evento(equipe, ev)) & candidatos
                for uid in disp_cache[ev.id]:
                    proxima_vaga.setdefault(uid, opp)

        if proxima_vaga:
            pessoas = list(
                User.objects
                .filter(id__in=proxima_vaga.keys())
                .order_by('first_name', 'username')
            )
            for p in pessoas:
                p.proxima_vaga = proxima_vaga[p.id]
            disponiveis_ociosos.append({'equipe': equipe, 'pessoas': pessoas})
            ociosos_total += len(pessoas)

    contexto = {
        'equipes': equipes,
        'total_futuras': futuras.count(),
        'buracos_total': buracos.count(),
        'designadas_total': designadas_total,
        'confirmadas': confirmadas,
        'a_confirmar': designadas_total - confirmadas,
        'taxa_confirmacao': round(100 * confirmadas / designadas_total) if designadas_total else 0,
        'buracos': buracos[:25],
        'ranking': ranking,
        'impedimentos': impedimentos[:25],
        'trocas_abertas': trocas_abertas[:25],
        'pendencias_total': impedimentos.count() + trocas_abertas.count(),
        'disponiveis_ociosos': disponiveis_ociosos,
        'ociosos_total': ociosos_total,
        'alguem_escalado_no_mes': alguem_escalado_no_mes,
        'mes_referencia': agora_local,
    }
    return render(request, 'equipe/dashboard_lider.html', contexto)
