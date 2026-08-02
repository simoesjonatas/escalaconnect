import calendar

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala.models import Escala, Desistencia, SolicitacaoTroca
from disponivel.models import Disponivel
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

    # Voluntários "ociosos": cadastraram disponibilidade neste mês mas ainda não
    # entraram em nenhuma escala da equipe no mês — o líder pode aproveitá-los.
    agora_local = localtime(now())
    inicio_mes = agora_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ultimo_dia = calendar.monthrange(agora_local.year, agora_local.month)[1]
    fim_mes = agora_local.replace(
        day=ultimo_dia, hour=23, minute=59, second=59, microsecond=999999
    )

    disponiveis_ociosos = []
    ociosos_total = 0
    for equipe in equipes:
        membros_ids = list(
            MembrosEquipe.objects
            .filter(equipe=equipe, aprovado=True)
            .values_list('usuario_id', flat=True)
        )
        if not membros_ids:
            continue
        # Quem tem disponibilidade que cobre qualquer parte deste mês.
        com_disponibilidade = set(
            Disponivel.objects
            .filter(
                usuario_id__in=membros_ids,
                data_inicio__lte=fim_mes,
                data_fim__gte=inicio_mes,
            )
            .values_list('usuario_id', flat=True)
        )
        if not com_disponibilidade:
            continue
        # Quem já foi escalado na equipe em algum evento do mês.
        ja_escalados = set(
            Escala.objects
            .filter(
                funcao__equipe=equipe,
                usuario_id__in=com_disponibilidade,
                evento__data_inicio__gte=inicio_mes,
                evento__data_inicio__lte=fim_mes,
            )
            .values_list('usuario_id', flat=True)
        )
        ociosos_ids = com_disponibilidade - ja_escalados
        if ociosos_ids:
            pessoas = list(
                User.objects
                .filter(id__in=ociosos_ids)
                .order_by('first_name', 'username')
            )
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
        'mes_referencia': agora_local,
    }
    return render(request, 'equipe/dashboard_lider.html', contexto)
