from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DisponivelForm
from .models import Disponivel
from ocupado.models import Ocupado
from django.contrib import messages
from datetime import timedelta
from evento.models import Evento
from django.utils import timezone

from django.core.paginator import Paginator

@login_required
def lista_disponivel(request):
    hoje = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    query = request.GET.get('q', '')
    order_by = request.GET.get('order_by', 'data_inicio')
    direction = request.GET.get('direction', 'asc')

    # Filtrar disponibilidades pelo usuário logado e com datas a partir de hoje
    disponiveis = Disponivel.objects.filter(usuario=request.user, data_inicio__gte=hoje, data_fim__gte=hoje)

    if query:
        disponiveis = disponiveis.filter(data_inicio__icontains=query)

    if direction == 'desc':
        order_by = '-' + order_by

    disponiveis = disponiveis.order_by(order_by)
    paginator = Paginator(disponiveis, 10)  # Mostrar 10 disponibilidades por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'disponivel/lista.html', {
        'page_obj': page_obj,
        'query': query,
        'order_by': order_by.strip('-'),
        'direction': 'asc' if direction == 'desc' else 'desc'
    })

@login_required
def detalhes_disponivel(request, pk):
    disponivel = get_object_or_404(Disponivel, pk=pk, usuario=request.user)  # Restringe a visualização ao dono
    return render(request, 'disponivel/detalhes.html', {'disponivel': disponivel})

@login_required
def registrar_disponibilidade_view(request):
    return render(request, 'disponivel/registrar_disponibilidade.html')

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


@login_required
def registrar_por_evento(request):
    # hoje = datetime.now()
    hoje = timezone.now()
    daqui_a_dois_meses = hoje + timedelta(days=60)  # Ajusta para dois meses a frente
    user = request.user

    # Pega os IDs dos eventos para os quais o usuário ja registrou uma disponibilidade
    eventos_indisponiveis_ids = Disponivel.objects.filter(usuario=user,evento__isnull=False).values_list('evento_id', flat=True)
    # print(eventos_indisponiveis_ids)

    # Filtra eventos futuros, excluindo aqueles para os quais o usuario ja registrou disponibilidade
    eventos_futuros = Evento.objects.filter(
        data_inicio__gte=hoje, 
        data_inicio__lte=daqui_a_dois_meses
    ).exclude(id__in=eventos_indisponiveis_ids).order_by('data_inicio')
    return render(request, 'disponivel/registrar_por_evento.html', {'eventos': eventos_futuros})

@login_required
def processar_disponibilidade_evento(request):
    if request.method == 'POST':
        selected_event_ids = request.POST.getlist('event_ids')
        # print(selected_event_ids)
        for event_id in selected_event_ids:
            # Crie aqui os registros de disponibilidade
            # print(event_id)
            evento = get_object_or_404(Evento, pk=event_id)
            # verifica se ja existe um registro de disponibilidade
            already_exists = Disponivel.objects.filter(usuario=request.user, evento=evento).exists()
            if not already_exists:

                Disponivel.objects.create(
                    usuario=request.user,
                    evento=evento,
                    data_inicio=evento.data_inicio,
                    data_fim=evento.data_fim
                )
        return redirect('lista_disponivel') #certo
    return redirect('lista_disponivel') #errado
# HttpResponseRedirect('/caminho-de-erro/')