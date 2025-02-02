from django.shortcuts import render, redirect, get_object_or_404
from .forms import OcupadoForm
from .models import Ocupado
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden



# validar se o usuario ja foi escalado em algum evento no horario da indisponibilidade
@login_required  # Assegura que apenas usuários logados possam acessar esta view
def lista_ocupado(request):
    query = request.GET.get('q', '')
    order_by = request.GET.get('order_by', 'data_inicio')
    direction = request.GET.get('direction', 'asc')

    # Filtrar ocupados pelo usuário logado
    ocupados = Ocupado.objects.filter(usuario=request.user)

    if query:
        ocupados = ocupados.filter(data_inicio__icontains=query)

    if direction == 'desc':
        order_by = '-' + order_by

    ocupados = ocupados.order_by(order_by)
    paginator = Paginator(ocupados, 10)  # Mostrar 10 ocupados por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'ocupado/lista.html', {
        'page_obj': page_obj,
        'query': query,
        'order_by': order_by.strip('-'),
        'direction': 'asc' if direction == 'desc' else 'desc'
    })

@login_required
def adicionar_ocupado(request):
    if request.method == "POST":
        form = OcupadoForm(request.POST)
        if form.is_valid():
            ocupado = form.save(commit=False)
            ocupado.usuario = request.user  # Setar o usuário logado como o usuário do objeto Ocupado
            ocupado.save()
            return redirect('lista_ocupado')
    else:
        form = OcupadoForm()
    return render(request, 'ocupado/adicionar.html', {'form': form})

@login_required
def detalhes_ocupado(request, pk):
    ocupado = get_object_or_404(Ocupado, pk=pk)
    return render(request, 'ocupado/detalhes.html', {'ocupado': ocupado})

@login_required
def atualizar_ocupado(request, pk):
    ocupado = get_object_or_404(Ocupado, pk=pk)

    if ocupado.usuario != request.user:
        return HttpResponseForbidden("Você não tem permissão para editar esta indisponibilidade.")

    if request.method == "POST":
        form = OcupadoForm(request.POST, instance=ocupado)
        if form.is_valid():
            form.save()
            return redirect('detalhes_ocupado', pk=ocupado.pk)
    else:
        form = OcupadoForm(instance=ocupado)

    return render(request, 'ocupado/atualizar.html', {'form': form})

@login_required
def excluir_ocupado(request, pk):
    ocupado = get_object_or_404(Ocupado, pk=pk)
    if request.method == 'POST':
        ocupado.delete()
        return redirect('lista_ocupado')
    return render(request, 'ocupado/confirmar_exclusao.html', {'ocupado': ocupado})
