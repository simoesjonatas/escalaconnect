from django.shortcuts import render, redirect, get_object_or_404
from .forms import OcupadoForm
from .models import Ocupado
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from disponivel.models import  Disponivel


# validar se o usuario ja foi escalado em algum evento no horario da indisponibilidade
@login_required
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
            novo_ocupado = form.save(commit=False)
            novo_ocupado.usuario = request.user

            # Verificar se existe alguma disponibilidade no mesmo horário
            conflitos = Disponivel.objects.filter(
                usuario=request.user,
                data_inicio__lt=novo_ocupado.data_fim,
                data_fim__gt=novo_ocupado.data_inicio
            )
            if conflitos.exists():
                messages.error(request, "Existe uma disponibilidade registrada que conflita com este período de indisponibilidade.")
                return render(request, 'ocupado/adicionar.html', {'form': form})
            
            novo_ocupado.save()
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
            ocupado_atualizado = form.save(commit=False)

            # Verificar conflitos com disponibilidades
            conflitos = Disponivel.objects.filter(
                usuario=request.user,
                data_inicio__lt=ocupado_atualizado.data_fim,
                data_fim__gt=ocupado_atualizado.data_inicio
            )
            if conflitos.exists():
                messages.error(request, "Existe uma disponibilidade registrada que conflita com este período de indisponibilidade.")
                return render(request, 'ocupado/atualizar.html', {'form': form})

            ocupado_atualizado.save()
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
