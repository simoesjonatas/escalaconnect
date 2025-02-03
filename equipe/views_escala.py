from django.shortcuts import render, get_object_or_404
from .models import Equipe
from escala.models import Escala
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

def listar_escalas(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    
    order_by = request.GET.get('order_by', 'evento__data_inicio')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')
    
    if direction == 'desc':
        order_by = f'-{order_by}'

    # Filter escalas from today onwards
    current_date = timezone.now()
    escalas_list = Escala.objects.filter(funcao__equipe=equipe, evento__data_inicio__gte=current_date).order_by(order_by)
    
    if query:
        escalas_list = escalas_list.filter(
            Q(evento__nome__icontains=query) | 
            Q(funcao__nome__icontains=query) |
            Q(usuario__username__icontains=query) |
            Q(funcao__equipe__nome__icontains=query)
        ).order_by(order_by)

    paginator = Paginator(escalas_list, 10)  # Display 10 escalas per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'equipe/escalas_equipe.html', {
        'equipe': equipe,
        'page_obj': page_obj,
        'order_by': order_by.strip('-'),
        'direction': direction,
        'query': query,
        'escala_fields': [
            ('evento__nome', 'Evento'),
            ('evento__data_inicio', 'Data Início'),
            ('funcao__nome', 'Função'),
            ('usuario__username', 'Usuário'),
            ('confirmada', 'Confirmada'),
        ]
    })


