from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from equipe.models import Equipe
from escala.models import Funcao
from escala.funcao_forms import FuncaoForm
from equipe.decorators import require_lideranca  # Importando o decorador personalizado



def funcao_list(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    
    # Configurações de ordenação e busca
    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'
    
    # Filtragem e ordenação das funções
    funcoes = equipe.funcao_set.filter(
        Q(nome__icontains=query)
    ).order_by(order_by)
    
    # Paginação
    paginator = Paginator(funcoes, 10)  # Mostra 10 funções por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Campos para ordenação
    funcao_fields = [
        ('id', 'ID'),
        ('nome', 'Nome'),
    ]

    context = {
        'equipe': equipe,
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'funcao_fields': funcao_fields,
        'query': query
    }
    return render(request, 'funcao/funcao_list.html', context)

@require_lideranca
def funcao_detail(request, pk):
    funcao = get_object_or_404(Funcao, pk=pk)
    return render(request, 'funcao/funcao_detail.html', {'funcao': funcao})

@require_lideranca
def funcao_create(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    if request.method == 'POST':
        form = FuncaoForm(request.POST, equipe=equipe)  # Passando a equipe
        if form.is_valid():
            funcao = form.save(commit=False)
            funcao.equipe = equipe
            funcao.save()
            return redirect(reverse('listar_funcoes', args=[equipe_pk]))
    else:
        form = FuncaoForm(equipe=equipe)  # Passando a equipe também no GET
    
    return render(request, 'funcao/funcao_form.html', {'form': form, 'equipe': equipe})

@require_lideranca
def funcao_update(request, pk):
    funcao = get_object_or_404(Funcao, pk=pk)
    if request.method == 'POST':
        form = FuncaoForm(request.POST, instance=funcao)
        if form.is_valid():
            form.save()
            return redirect('listar_funcoes', equipe_pk=funcao.equipe.pk)
    else:
        form = FuncaoForm(instance=funcao)
    
    return render(request, 'funcao/funcao_form.html', {'form': form, 'funcao': funcao,  'equipe': funcao.equipe})

@require_lideranca
def funcao_delete(request, pk):
    funcao = get_object_or_404(Funcao, pk=pk)
    if request.method == 'POST':
        funcao.delete()
        return redirect('listar_funcoes', equipe_pk=funcao.equipe.pk)
    
    return render(request, 'funcao/funcao_confirm_delete.html', {'funcao': funcao})
