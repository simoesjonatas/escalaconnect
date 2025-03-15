from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from .forms import EquipeForm
from equipe.decorators import require_lideranca  # Importando o decorador personalizado
from escalaconnect.utils import admin_required
from django.contrib.auth.decorators import login_required
from .models import Equipe, MembrosEquipe
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef


def equipe_list(request):
    query = request.GET.get('q', '')
    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')

    if direction == 'desc':
        order_by = f'-{order_by}'

    equipes = Equipe.objects.filter(nome__icontains=query).order_by(order_by)

    paginator = Paginator(equipes, 10)  # Exibe 10 equipes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    fields = [
        ('id', 'ID'),
        ('nome', 'Nome'),
    ]

    context = {
        'page_obj': page_obj,
        'query': query,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'fields': fields,
    }
    return render(request, 'equipe/equipe_list.html', context)

@admin_required
def equipe_create(request):
    if request.method == 'POST':
        form = EquipeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('equipe_list')
    else:
        form = EquipeForm()
    return render(request, 'equipe/equipe_form.html', {'form': form})

@require_lideranca
@admin_required
def equipe_update(request, pk):
    equipe = get_object_or_404(Equipe, pk=pk)
    if request.method == 'POST':
        form = EquipeForm(request.POST, instance=equipe)
        if form.is_valid():
            form.save()
            return redirect('equipe_list')
    else:
        form = EquipeForm(instance=equipe)
    return render(request, 'equipe/equipe_form.html', {'form': form})

@require_lideranca
@admin_required
def equipe_delete(request, pk):
    equipe = get_object_or_404(Equipe, pk=pk)
    if request.method == 'POST':
        equipe.delete()
        return redirect('equipe_list')
    return render(request, 'equipe/equipe_confirm_delete.html', {'equipe': equipe})

@require_lideranca
def equipe_detail(request, pk):
    equipe = get_object_or_404(Equipe, pk=pk)
    return render(request, 'equipe/equipe_detail.html', {'equipe': equipe})

@login_required
def candidatura_equipe(request):
    # subquery para verificar se o usuario e membro pendente ou aprovado de cada equipe
    pendente_subquery = MembrosEquipe.objects.filter(
        equipe=OuterRef('pk'), 
        usuario=request.user, 
        aprovado=False
    )
    aprovado_subquery = MembrosEquipe.objects.filter(
        equipe=OuterRef('pk'), 
        usuario=request.user, 
        aprovado=True
    )

    # busca todas as equipes onde o usuario pode se candidatar ou cancelar a candidatura
    todas_equipes = Equipe.objects.annotate(
        is_member_pendente=Exists(pendente_subquery),
        is_member_aprovado=Exists(aprovado_subquery)
    ).filter(Q(is_member_pendente=True) | ~Q(is_member_aprovado=True))

    context = {
        'equipes': todas_equipes
    }

    if request.method == 'POST':
        candidatar_ids = request.POST.getlist('candidatar_ids')
        cancelar_ids = request.POST.getlist('cancelar_ids')

        # processar candidaturas
        for equipe_id in candidatar_ids:
            equipe = Equipe.objects.get(id=equipe_id)
            MembrosEquipe.objects.get_or_create(usuario=request.user, equipe=equipe)

        # processar cancelamentos
        for equipe_id in cancelar_ids:
            equipe = Equipe.objects.get(id=equipe_id)
            MembrosEquipe.objects.filter(usuario=request.user, equipe=equipe).delete()

        messages.success(request, 'Suas candidaturas foram atualizadas com sucesso!')
        return redirect('equipe_list')

    return render(request, 'equipe/candidatura_equipe.html', context)
