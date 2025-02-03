from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DisponivelForm
from .models import Disponivel
from ocupado.models import Ocupado
from django.contrib import messages

@login_required
def lista_disponivel(request):
    disponiveis = Disponivel.objects.filter(usuario=request.user)
    return render(request, 'disponivel/lista.html', {'disponiveis': disponiveis})

@login_required
def detalhes_disponivel(request, pk):
    disponivel = get_object_or_404(Disponivel, pk=pk, usuario=request.user)  # Restringe a visualização ao dono
    return render(request, 'disponivel/detalhes.html', {'disponivel': disponivel})

@login_required
def adicionar_disponivel(request):
    if request.method == "POST":
        form = DisponivelForm(request.POST)
        if form.is_valid():
            nova_disponivel = form.save(commit=False)
            nova_disponivel.usuario = request.user
            
            # Verificar se existe alguma indisponibilidade no mesmo horário
            conflitos = Ocupado.objects.filter(
                usuario=request.user,
                data_inicio__lt=nova_disponivel.data_fim,
                data_fim__gt=nova_disponivel.data_inicio
            )
            if conflitos.exists():
                messages.error(request, "Existe uma indisponibilidade registrada que conflita com este período de disponibilidade.")
                return render(request, 'disponivel/adicionar.html', {'form': form})
            
            nova_disponivel.save()
            return redirect('lista_disponivel')
    else:
        form = DisponivelForm()
    return render(request, 'disponivel/adicionar.html', {'form': form})

@login_required
def editar_disponivel(request, pk):
    disponivel = get_object_or_404(Disponivel, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = DisponivelForm(request.POST, instance=disponivel)
        if form.is_valid():
            disponivel_atualizada = form.save(commit=False)
            
            # Verificar conflitos com indisponibilidades
            conflitos = Ocupado.objects.filter(
                usuario=request.user,
                data_inicio__lt=disponivel_atualizada.data_fim,
                data_fim__gt=disponivel_atualizada.data_inicio
            )
            if conflitos.exists():
                messages.error(request, "Existe uma indisponibilidade registrada que conflita com este período de disponibilidade.")
                return render(request, 'disponivel/editar.html', {'form': form})

            disponivel_atualizada.save()
            return redirect('lista_disponivel')
    else:
        form = DisponivelForm(instance=disponivel)
    return render(request, 'disponivel/editar.html', {'form': form})

@login_required
def excluir_disponivel(request, pk):
    disponivel = get_object_or_404(Disponivel, pk=pk, usuario=request.user)
    if request.method == 'POST':
        disponivel.delete()
        return redirect('lista_disponivel')
    return render(request, 'disponivel/confirmar_exclusao.html', {'disponivel': disponivel})
