from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from .models import Planejamento, PlanejamentoFuncao
from .forms import PlanejamentoForm, PlanejamentoFuncaoForm
from django.forms import inlineformset_factory

def planejamento_list(request):
    query = request.GET.get('q', '')
    planejamentos = Planejamento.objects.filter(nome__icontains=query).order_by('-data_cadastro')

    paginator = Paginator(planejamentos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'planejamento/planejamento_list.html', {'page_obj': page_obj, 'query': query})


def planejamento_create(request):
    PlanejamentoFuncaoFormSet = inlineformset_factory(
        Planejamento,
        PlanejamentoFuncao,
        form=PlanejamentoFuncaoForm,
        extra=1,
        can_delete=True,
    )

    if request.method == "POST":
        form = PlanejamentoForm(request.POST)
        planejamento = Planejamento()
        formset = PlanejamentoFuncaoFormSet(
            request.POST,
            instance=planejamento,
            prefix="funcoes",
        )

        if form.is_valid() and formset.is_valid():
            planejamento = form.save()
            formset.instance = planejamento
            formset.save()
            return redirect('planejamento_list')
    else:
        form = PlanejamentoForm()
        formset = PlanejamentoFuncaoFormSet(
            instance=Planejamento(),
            prefix="funcoes",
        )

    context = {
        'form': form,
        'formset': formset,
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

    PlanejamentoFuncaoFormSet = inlineformset_factory(
        Planejamento,
        PlanejamentoFuncao,
        form=PlanejamentoFuncaoForm,
        extra=0,
        can_delete=True,
    )

    if request.method == 'POST':
        form = PlanejamentoForm(request.POST, instance=planejamento)
        formset = PlanejamentoFuncaoFormSet(
            request.POST,
            instance=planejamento,
            prefix="funcoes",
        )
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('planejamento_list')
    else:
        form = PlanejamentoForm(instance=planejamento)
        formset = PlanejamentoFuncaoFormSet(
            instance=planejamento,
            prefix="funcoes",
        )

    return render(request, 'planejamento/planejamento_form.html', {'form': form, 'formset': formset})

def planejamento_delete(request, pk):
    planejamento = get_object_or_404(Planejamento, pk=pk)

    if request.method == 'POST':
        planejamento.delete()
        return redirect('planejamento_list')

    return render(request, 'planejamento/planejamento_confirm_delete.html', {'planejamento': planejamento})

def planejamento_detail(request, pk):
    planejamento = get_object_or_404(Planejamento, pk=pk)
    return render(request, 'planejamento/planejamento_detail.html', {'planejamento': planejamento})
