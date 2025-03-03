from django.shortcuts import render, redirect, get_object_or_404
from .forms import OcupadoForm
from .models import Ocupado
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from disponivel.models import  Disponivel
# from django.http import HttpResponseRedirect
from datetime import datetime, timedelta
from evento.models import Evento
from django.utils import timezone

# validar se o usuario ja foi escalado em algum evento no horario da indisponibilidade
@login_required
def lista_ocupado(request):
    hoje = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    query = request.GET.get('q', '')
    order_by = request.GET.get('order_by', 'data_inicio')
    direction = request.GET.get('direction', 'asc')

    # Filtrar ocupados pelo usuário logado e com datas a partir de hoje
    ocupados = Ocupado.objects.filter(usuario=request.user, data_inicio__gte=hoje, data_fim__gte=hoje)

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

@login_required
def registrar_indisponibilidade_view(request):
    return render(request, 'ocupado/registrar_indisponibilidade.html')

@login_required
def processar_indisponibilidade_evento(request):
    if request.method == 'POST':
        selected_event_ids = request.POST.getlist('event_ids')
        # print(selected_event_ids)
        for event_id in selected_event_ids:
            # Crie aqui os registros de indisponibilidade...
            # print(event_id)
            evento = get_object_or_404(Evento, pk=event_id)
            # verifica se ja existe um registro de indisponibilidade
            already_exists = Ocupado.objects.filter(usuario=request.user, evento=evento).exists()
            if not already_exists:

                Ocupado.objects.create(
                    usuario=request.user,
                    evento=evento,
                    data_inicio=evento.data_inicio,
                    data_fim=evento.data_fim
                )
        return redirect('lista_ocupado') #certo
    return redirect('lista_ocupado') #errado
# HttpResponseRedirect('/caminho-de-erro/')


def registrar_por_evento(request):
    # hoje = datetime.now()
    hoje = timezone.now()
    daqui_a_dois_meses = hoje + timedelta(days=60)  # Ajusta para dois meses a frente
    user = request.user

    # Pega os IDs dos eventos para os quais o usuário ja registrou uma indisponibilidade
    eventos_indisponiveis_ids = Ocupado.objects.filter(usuario=user,evento__isnull=False).values_list('evento_id', flat=True)
    # print(eventos_indisponiveis_ids)

    # Filtra eventos futuros, excluindo aqueles para os quais o usuario ja registrou indisponibilidade
    eventos_futuros = Evento.objects.filter(
        data_inicio__gte=hoje, 
        data_inicio__lte=daqui_a_dois_meses
    ).exclude(id__in=eventos_indisponiveis_ids).order_by('data_inicio')
    return render(request, 'ocupado/registrar_por_evento.html', {'eventos': eventos_futuros})