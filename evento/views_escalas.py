from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from escala.models import Escala
from evento.models import Evento
from equipe.decorators import require_lideranca 


def escalas_por_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)

    # Configuração de ordenação e busca
    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    # Filtragem e ordenação das escalas
    escalas = Escala.objects.filter(
        evento=evento
    ).filter(
        Q(usuario__username__icontains=query) |
        Q(funcao__nome__icontains=query)
    ).order_by(order_by)

    # Paginação
    paginator = Paginator(escalas, 10)  # Exibe 10 escalas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Campos para ordenação
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
