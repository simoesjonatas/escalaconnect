from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from .models import Planejamento, PlanejamentoFuncao
from .forms import PlanejamentoForm
from escala.models import Funcao


def _funcoes_por_equipe():
    funcoes_por_equipe = {}
    funcoes = Funcao.objects.select_related('equipe').order_by('equipe__nome', 'nome')
    for funcao in funcoes:
        funcoes_por_equipe.setdefault(funcao.equipe, []).append(funcao)
    return funcoes_por_equipe


def _selected_funcoes_ids_from_request(request):
    return {
        int(value)
        for value in request.POST.getlist('funcoes')
        if value.isdigit()
    }


def _salvar_funcoes_planejamento(planejamento, funcao_ids):
    funcoes = Funcao.objects.filter(id__in=funcao_ids)
    PlanejamentoFuncao.objects.filter(planejamento=planejamento).delete()
    PlanejamentoFuncao.objects.bulk_create([
        PlanejamentoFuncao(planejamento=planejamento, funcao=funcao)
        for funcao in funcoes
    ])
    return funcoes.count()

def planejamento_list(request):
    query = request.GET.get('q', '')
    planejamentos = (
        Planejamento.objects
        .filter(nome__icontains=query)
        .prefetch_related('funcoes__funcao__equipe')
        .order_by('-data_cadastro')
    )

    paginator = Paginator(planejamentos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'planejamento/planejamento_list.html', {'page_obj': page_obj, 'query': query})


def planejamento_create(request):
    if request.method == "POST":
        form = PlanejamentoForm(request.POST)
        selected_funcoes = _selected_funcoes_ids_from_request(request)

        if not selected_funcoes:
            form.add_error(None, "Selecione pelo menos uma função para o planejamento.")

        if form.is_valid():
            with transaction.atomic():
                planejamento = form.save()
                total = _salvar_funcoes_planejamento(planejamento, selected_funcoes)
            messages.success(request, f"Planejamento criado com {total} função(ões).")
            return redirect('planejamento_detail', pk=planejamento.pk)
    else:
        form = PlanejamentoForm()
        selected_funcoes = set()

    context = {
        'form': form,
        'funcoes_por_equipe': _funcoes_por_equipe(),
        'selected_funcoes': selected_funcoes,
        'is_edit': False,
    }
    return render(request, 'planejamento/planejamento_form.html', context)


# def planejamento_create(request):
#     if request.method == 'POST':
#         form = PlanejamentoForm(request.POST)
#         if form.is_valid():
#             planejamento = form.save()
#             return redirect('planejamento_list')
#     else:
#         form = PlanejamentoForm()

#     return render(request, 'planejamento/planejamento_form.html', {'form': form})

def planejamento_update(request, pk):
    planejamento = get_object_or_404(Planejamento, pk=pk)

    if request.method == 'POST':
        form = PlanejamentoForm(request.POST, instance=planejamento)
        selected_funcoes = _selected_funcoes_ids_from_request(request)

        if not selected_funcoes:
            form.add_error(None, "Selecione pelo menos uma função para o planejamento.")

        if form.is_valid():
            with transaction.atomic():
                planejamento = form.save()
                total = _salvar_funcoes_planejamento(planejamento, selected_funcoes)
            messages.success(request, f"Planejamento atualizado com {total} função(ões).")
            return redirect('planejamento_detail', pk=planejamento.pk)
    else:
        form = PlanejamentoForm(instance=planejamento)
        selected_funcoes = set(
            PlanejamentoFuncao.objects
            .filter(planejamento=planejamento)
            .values_list('funcao_id', flat=True)
        )

    return render(request, 'planejamento/planejamento_form.html', {
        'form': form,
        'planejamento': planejamento,
        'funcoes_por_equipe': _funcoes_por_equipe(),
        'selected_funcoes': selected_funcoes,
        'is_edit': True,
    })

def planejamento_delete(request, pk):
    planejamento = get_object_or_404(Planejamento, pk=pk)

    if request.method == 'POST':
        planejamento.delete()
        return redirect('planejamento_list')

    return render(request, 'planejamento/planejamento_confirm_delete.html', {'planejamento': planejamento})

def planejamento_detail(request, pk):
    planejamento = get_object_or_404(
        Planejamento.objects.prefetch_related('funcoes__funcao__equipe'),
        pk=pk,
    )
    return render(request, 'planejamento/planejamento_detail.html', {'planejamento': planejamento})
