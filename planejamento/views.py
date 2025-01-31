from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from .models import Planejamento, PlanejamentoFuncao
from .forms import PlanejamentoForm, PlanejamentoFuncaoForm
from django.forms import modelformset_factory
from escala.models import Funcao

def planejamento_list(request):
    query = request.GET.get('q', '')
    planejamentos = Planejamento.objects.filter(nome__icontains=query).order_by('-data_cadastro')

    paginator = Paginator(planejamentos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'planejamento/planejamento_list.html', {'page_obj': page_obj, 'query': query})


def planejamento_create(request):
    planejamento = None
    if request.method == "POST":
        form = PlanejamentoForm(request.POST)
        funcao_formset = modelformset_factory(PlanejamentoFuncao, form=PlanejamentoFuncaoForm, extra=1)(request.POST)

        if form.is_valid() and funcao_formset.is_valid():
            planejamento = form.save()

            for funcao_form in funcao_formset:
                if funcao_form.cleaned_data:
                    funcao = funcao_form.save(commit=False)
                    funcao.planejamento = planejamento
                    funcao.save()

            return redirect('planejamento_list')
    else:
        form = PlanejamentoForm()
        funcao_formset = modelformset_factory(PlanejamentoFuncao, form=PlanejamentoFuncaoForm, extra=1)()

    context = {
        'form': form,
        'formset': funcao_formset,
        'funcoes_disponiveis': Funcao.objects.all(),
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
        if form.is_valid():
            form.save()
            return redirect('planejamento_list')
    else:
        form = PlanejamentoForm(instance=planejamento)

    return render(request, 'planejamento/planejamento_form.html', {'form': form})

def planejamento_delete(request, pk):
    planejamento = get_object_or_404(Planejamento, pk=pk)

    if request.method == 'POST':
        planejamento.delete()
        return redirect('planejamento_list')

    return render(request, 'planejamento/planejamento_confirm_delete.html', {'planejamento': planejamento})

def planejamento_detail(request, pk):
    planejamento = get_object_or_404(Planejamento, pk=pk)
    return render(request, 'planejamento/planejamento_detail.html', {'planejamento': planejamento})
