from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from escala.models import Escala
from evento.models import Evento
from escala.forms import EscalaForm
from equipe.decorators import require_lideranca 
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.contrib import messages
from ocupado.models import Ocupado



def escalas_por_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)

    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    escalas = Escala.objects.filter(
        evento=evento
    ).filter(
        Q(usuario__username__icontains=query) |
        Q(funcao__nome__icontains=query)
    ).order_by(order_by)

    paginator = Paginator(escalas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    escala_fields = [
        ('usuario__username', 'Usuário'),
        ('funcao__nome', 'Função'),
        ('confirmada', 'Confirmada'),
        ('data_confirmacao', 'Data de Confirmação'),
    ]

    context = {
        'evento': evento,
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'escala_fields': escala_fields,
        'query': query
    }
    return render(request, 'escala/escala_list.html', context)

@require_lideranca
def escala_create(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        form = EscalaForm(request.POST, evento=evento)
        if form.is_valid():
            escala = form.save(commit=False)
            escala.evento = evento
            escala.save()
            return redirect(reverse('evento_escalas', args=[pk]))
    else:
        form = EscalaForm(evento=evento)

    return render(request, 'escala/escala_form.html', {'form': form, 'evento': evento})

@require_lideranca
def escala_update(request, pk):
    escala = get_object_or_404(Escala, pk=pk)
    if request.method == 'POST':
        form = EscalaForm(request.POST, instance=escala)
        if form.is_valid():
            form.save()
            return redirect('evento_escalas', pk=escala.evento.pk)
    else:
        form = EscalaForm(instance=escala)

    return render(request, 'escala/escala_form.html', {'form': form, 'escala': escala, 'evento': escala.evento})

@require_lideranca
def escala_delete(request, pk):
    escala = get_object_or_404(Escala, pk=pk)
    if request.method == 'POST':
        escala.delete()
        return redirect('evento_escalas', pk=escala.evento.pk)

    return render(request, 'escala/escala_confirm_delete.html', {'escala': escala})

# @require_lideranca
def escala_detail(request, pk):
    escala = get_object_or_404(Escala, pk=pk)
    # pega os horários do evento associado a escala
    evento_inicio = escala.evento.data_inicio
    evento_fim = escala.evento.data_fim

    # pega os membros da equipe e filtra aqueles sem indisponibilidade
    membros = escala.funcao.equipe.membros.all()
    usuarios_disponiveis = [membro.usuario for membro in membros if not Ocupado.objects.filter(
        usuario=membro.usuario,
        data_inicio__lt=evento_fim,
        data_fim__gt=evento_inicio
    ).exists()]
    
    return render(request, 'escala/escala_detail.html', 
                {'escala': escala,
                'usuarios_disponiveis': usuarios_disponiveis
})


@login_required
def minhas_escalas(request):
    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    escalas = Escala.objects.filter(
        usuario=request.user  # Filtra apenas escalas do usuário autenticado
    ).filter(
        Q(evento__nome__icontains=query) |
        Q(funcao__equipe__nome__icontains=query) |
        Q(funcao__nome__icontains=query)
    ).order_by(order_by)

    paginator = Paginator(escalas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    escala_fields = [
        ('evento__nome', 'Evento'),
        ('funcao__equipe__nome', 'Equipe'),
        ('funcao__nome', 'Função'),
        ('confirmada', 'Confirmada'),
        ('data_confirmacao', 'Data de Confirmação'),
    ]

    context = {
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'escala_fields': escala_fields,
        'query': query
    }
    return render(request, 'escala/minhas_escalas.html', context)


@login_required
def minha_escala_detail(request, pk):
    escala = get_object_or_404(Escala, pk=pk, usuario=request.user)
    return render(request, 'escala/minha_escala_detail.html', {'escala': escala})

@login_required
def confirmar_minha_escala(request, pk):
    escala = get_object_or_404(Escala, pk=pk)

    # Verifica se o usuário logado é o dono da escala
    if escala.usuario != request.user:
        messages.error(request, "Você só pode confirmar sua própria escala.")
        return redirect('minhas_escalas')

    # Verifica se o evento já foi encerrado
    if escala.evento.data_fim < now():
        messages.error(request, "Você não pode confirmar uma escala de um evento já encerrado.")
        return redirect('minha_escala_detail', pk=escala.pk)

    # Verifica se a escala já foi confirmada
    if escala.confirmada:
        messages.warning(request, "Esta escala já foi confirmada anteriormente.")
        return redirect('minha_escala_detail', pk=escala.pk)

    # Confirma a escala apenas se for uma requisição POST
    if request.method == 'POST':
        escala.confirmada = True
        escala.data_confirmacao = now()
        escala.save()
        messages.success(request, "Escala confirmada com sucesso!")

    return redirect('minha_escala_detail', pk=escala.pk)