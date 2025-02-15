from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from equipe.models import Equipe, MembrosEquipe
from equipe.membros_forms import MembrosEquipeForm
from equipe.decorators import require_lideranca


@require_lideranca
def membros_equipe_list(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    
    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'
    
    # membros = equipe.membrosequipe_set.filter(
    #     Q(usuario__username__icontains=query)
    # ).order_by(order_by)
    
    membros = equipe.membros.filter(
        Q(usuario__username__icontains=query) & Q(aprovado=True)
    ).order_by(order_by)
    
    paginator = Paginator(membros, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    membros_fields = [
        ('id', 'ID'),
        ('usuario', 'Membro'),
    ]

    context = {
        'equipe': equipe,
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'membros_fields': membros_fields,
        'query': query
    }
    return render(request, 'membros_equipe/membros_equipe_list.html', context)

@require_lideranca
def membros_equipe_detail(request,equipe_pk, pk):
    membro = get_object_or_404(MembrosEquipe, pk=pk)
    return render(request, 'membros_equipe/membros_equipe_detail.html', {'membro': membro})

@require_lideranca
def membros_equipe_create(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    if request.method == 'POST':
        form = MembrosEquipeForm(request.POST, equipe=equipe)
        if form.is_valid():
            membro = form.save(commit=False)
            membro.equipe = equipe
            membro.aprovado = True
            membro.save()
            return redirect(reverse('listar_membros_equipe', args=[equipe_pk]))
    else:
        form = MembrosEquipeForm(equipe=equipe)
    
    return render(request, 'membros_equipe/membros_equipe_form.html', {'form': form, 'equipe': equipe})

@require_lideranca
def membros_equipe_update(request, equipe_pk, pk):
    membro = get_object_or_404(MembrosEquipe, pk=pk)
    if request.method == 'POST':
        form = MembrosEquipeForm(request.POST, instance=membro)
        if form.is_valid():
            form.save()
            return redirect('listar_membros_equipe', equipe_pk=membro.equipe.pk)
    else:
        form = MembrosEquipeForm(instance=membro)
    
    return render(request, 'membros_equipe/membros_equipe_form.html', {'form': form, 'membro': membro, 'equipe': membro.equipe})

@require_lideranca
def membros_equipe_delete(request, equipe_pk, pk):
    membro = get_object_or_404(MembrosEquipe, pk=pk)
    if request.method == 'POST':
        membro.delete()
        return redirect('listar_membros_equipe', equipe_pk=membro.equipe.pk)
    
    return render(request, 'membros_equipe/membros_equipe_confirm_delete.html', {'membro': membro})
