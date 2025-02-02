from django.http import JsonResponse
from .models import Evento
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .forms import EventoForm
from escalaconnect.utils import admin_required
from equipe.decorators import require_lideranca 
from django.utils.timezone import now


def eventos_api(request):
    eventos = Evento.objects.all()
    data = []
    for evento in eventos:
        data.append({
            'id': evento.id, 
            'title': evento.nome,
            'start': evento.data_inicio.isoformat(),
            'end': evento.data_fim.isoformat(),
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