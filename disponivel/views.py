from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DisponivelForm
from .models import Disponivel
from ocupado.models import Ocupado
from django.contrib import messages
from datetime import timedelta
from evento.models import Evento
from django.utils import timezone
from escalaconnect.regras import RegraDeNegocio
from .services import disponibilidades

from django.core.paginator import Paginator

@login_required
def lista_disponivel(request):
    query = request.GET.get('q', '')
    order_by = request.GET.get('order_by', 'data_inicio')
    direction = request.GET.get('direction', 'asc')

    # Filtrar disponibilidades pelo usuário logado e com datas a partir de hoje
    disponiveis = disponibilidades.futuros(request.user)

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
            try:
                disponibilidades.validar(request.user, nova_disponivel.data_inicio, nova_disponivel.data_fim)
            except RegraDeNegocio as erro:
                messages.error(request, str(erro))
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
            try:
                disponibilidades.validar(request.user, disponivel_atualizada.data_inicio, disponivel_atualizada.data_fim)
            except RegraDeNegocio as erro:
                messages.error(request, str(erro))
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
    # Eventos dos próximos dois meses, visíveis ao usuário, ainda sem disponibilidade dele.
    eventos_futuros = disponibilidades.eventos_elegiveis(request.user)

    # Equipes dos eventos privados (de equipe) presentes na lista. O filtro por
    # equipe só é exibido se houver ao menos um evento de equipe aqui.
    equipes_eventos = list(
        eventos_futuros.filter(equipe__isnull=False)
        .values_list('equipe_id', 'equipe__nome')
        .distinct()
        .order_by('equipe__nome')
    )

    return render(request, 'disponivel/registrar_por_evento.html', {
        'eventos': eventos_futuros,
        'equipes_eventos': equipes_eventos,
    })

@login_required
def processar_disponibilidade_evento(request):
    if request.method == 'POST':
        selected_event_ids = [i for i in request.POST.getlist('event_ids') if i.isdigit()]
        # Cria uma disponibilidade por evento visível que ainda não tenha registro.
        criadas = disponibilidades.registrar_por_eventos(request.user, selected_event_ids)
        if criadas:
            messages.success(request, f"{criadas} disponibilidade(s) registrada(s) com sucesso.")
        return redirect('lista_disponivel') #certo
    return redirect('lista_disponivel') #errado
# HttpResponseRedirect('/caminho-de-erro/')
