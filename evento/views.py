from django.http import JsonResponse
from .models import Evento
from django.views.decorators.csrf import csrf_exempt
import json
from escala.models import Escala
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .forms import EventoForm
from escalaconnect.utils import admin_required
from equipe.decorators import require_lideranca 
from django.utils.timezone import now
from escalaconnect.tasks import enviar_email_confirmacao_task
from django.contrib import messages



def eventos_api(request):
    eventos = Evento.objects.all().order_by('data_inicio')

    # Escalas do usuário logado, para colorir o calendário com as próprias escalas.
    minhas = {}
    if request.user.is_authenticated:
        escalas = Escala.objects.filter(usuario=request.user).select_related('funcao')
        for esc in escalas:
            info = minhas.setdefault(esc.evento_id, {'confirmada': True, 'funcoes': []})
            if esc.funcao:
                info['funcoes'].append(esc.funcao.nome)
            if not esc.confirmada:
                info['confirmada'] = False

    data = []
    for evento in eventos:
        mine = minhas.get(evento.id)
        if mine and mine['confirmada']:
            cor, status = '#2e7d32', 'Confirmada'   # verde
        elif mine:
            cor, status = '#ef6c00', 'A confirmar'   # laranja
        else:
            cor, status = '#3b5bdb', None            # azul

        data.append({
            'id': evento.id,
            'title': evento.nome,
            'start': evento.data_inicio.isoformat(),
            'end': evento.data_fim.isoformat(),
            'backgroundColor': cor,
            'borderColor': cor,
            'extendedProps': {
                'escalado': bool(mine),
                'status': status,
                'funcoes': ', '.join(mine['funcoes']) if mine else '',
            },
        })
    return JsonResponse(data, safe=False)

@require_lideranca
@csrf_exempt  # Permite chamadas AJAX sem CSRF token (melhor adicionar autenticação em produção)
def criar_evento(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        evento = Evento.objects.create(
            nome=data['title'],
            data_inicio=data['start'],
            data_fim=data['end']
        )
        
        return JsonResponse({"success": True, "id": evento.id})

    return JsonResponse({"error": "Método inválido"}, status=400)

@csrf_exempt
@require_lideranca
def atualizar_evento(request, event_id):
    if request.method == 'PUT':
        data = json.loads(request.body)
        try:
            evento = Evento.objects.get(id=event_id)
            evento.nome = data['title']
            evento.data_inicio = data['start']
            evento.data_fim = data['end']
            evento.save()
            return JsonResponse({"success": True})
        except Evento.DoesNotExist:
            return JsonResponse({"error": "Evento não encontrado"}, status=404)
    return JsonResponse({"error": "Método inválido"}, status=400)

@require_lideranca
@csrf_exempt
def excluir_evento(request, event_id):
    if request.method == 'DELETE':
        try:
            evento = Evento.objects.get(id=event_id)
            evento.delete()
            return JsonResponse({"success": True})
        except Evento.DoesNotExist:
            return JsonResponse({"error": "Evento não encontrado"}, status=404)
    return JsonResponse({"error": "Método inválido"}, status=400)

def evento_list(request):
    query = request.GET.get('q', '')
    order_by = request.GET.get('order_by', 'data_inicio')
    direction = request.GET.get('direction', 'asc')

    if direction == 'desc':
        order_by = f'-{order_by}'
    
    today = now().date()

    eventos = Evento.objects.filter(
        data_inicio__date__gte=today,
        nome__icontains=query).order_by(order_by)

    paginator = Paginator(eventos, 10)  # Exibe 10 eventos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    fields = [
        ('id', 'ID'),
        ('nome', 'Nome'),
        ('data_inicio', 'Data de Início'),
        ('data_fim', 'Data de Fim'),
    ]

    context = {
        'page_obj': page_obj,
        'query': query,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'fields': fields,
    }
    return render(request, 'evento/evento_list.html', context)

@require_lideranca
def evento_create(request):
    if request.method == 'POST':
        form = EventoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('evento_list')
    else:
        form = EventoForm()
    return render(request, 'evento/evento_form.html', {'form': form})

@require_lideranca
def evento_update(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        form = EventoForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()
            return redirect('evento_list')
    else:
        form = EventoForm(instance=evento)
    return render(request, 'evento/evento_form.html', {'form': form})

@require_lideranca
def evento_delete(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if request.method == 'POST':
        evento.delete()
        return redirect('evento_list')
    return render(request, 'evento/evento_confirm_delete.html', {'evento': evento})

def evento_detail(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    return render(request, 'evento/evento_detail.html', {'evento': evento})

def view_enviar_confirmacao(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)

    escalas_nao_confirmadas = (
        Escala.objects
        .filter(evento=evento, confirmada=False)
        .select_related("usuario", "funcao", "funcao__equipe")
        .exclude(usuario__email__isnull=True)
        .exclude(usuario__email__exact="")
    )

    total = escalas_nao_confirmadas.count()
    for escala in escalas_nao_confirmadas:
        enviar_email_confirmacao_task.delay(escala.id)

    if total:
        messages.success(request, f"{total} e-mail(s) de confirmação publicado(s) para envio.")
    else:
        messages.info(request, "Ninguém pendente de confirmação com e-mail cadastrado.")

    return redirect('evento_detail', pk=evento_id)

def view_enviar_lembrete(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)

    escalas_pendentes = (
        Escala.objects
        .filter(evento=evento, confirmada=False)
        .select_related("usuario", "funcao", "funcao__equipe")
        .exclude(usuario__email__isnull=True)
        .exclude(usuario__email__exact="")
    )

    total = escalas_pendentes.count()
    for escala in escalas_pendentes:
        enviar_email_confirmacao_task.delay(escala.id)

    if total:
        messages.success(request, f"{total} lembrete(s) de escala publicado(s) para envio.")
    else:
        messages.info(request, "Ninguém pendente de lembrete com e-mail cadastrado.")
    return redirect('evento_detail', pk=evento_id)
