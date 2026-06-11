from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from equipe.models import Equipe, Lideranca, MembrosEquipe
from escala.models import Escala
from django.utils.timezone import now
from equipe.lideranca_forms import LiderancaForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from escalaconnect.utils import admin_required
from equipe.decorators import require_lideranca  # Importando o decorador personalizado


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
        equipes = Equipe.objects.all()
    else:
        equipes = Equipe.objects.filter(lideranca__usuario=request.user).distinct()

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
    }
    return render(request, 'equipe/dashboard_lider.html', contexto)
