from django.shortcuts import render, get_object_or_404
from .models import Equipe, Lideranca
from escala.models import Escala, Desistencia
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from ocupado.models import Ocupado
from disponivel.models import Disponivel

def get_unapproved_desistencias(equipe_id):
    equipe = get_object_or_404(Equipe, pk=equipe_id)
    
    # Realiza a consulta para obter desistências não aprovadas
    desistencias = Desistencia.objects.filter(
        escala__funcao__equipe=equipe, 
        aprovada=False
    )
    
    return desistencias

def listar_escalas(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    
    order_by = request.GET.get('order_by', 'evento__data_inicio')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')
    
    if direction == 'desc':
        order_by = f'-{order_by}'

    # Filter escalas from today onwards
    # current_date = timezone.now()
    today = timezone.now().date()
    escalas_list = Escala.objects.filter(
        funcao__equipe=equipe, 
        evento__data_inicio__date__gte=today
        ).order_by(order_by)
    
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
    
    # desistencias =get_unapproved_desistencias(equipe.pk)

    return render(request, 'equipe/escalas_equipe.html', {
        'equipe': equipe,
        'page_obj': page_obj,
        'order_by': order_by.strip('-'),
        'direction': direction,
        'query': query,
        # 'desistencias': desistencias,
        'escala_fields': [
            ('evento__nome', 'Evento'),
            ('evento__data_inicio', 'Data Início'),
            ('funcao__nome', 'Função'),
            ('usuario__username', 'Usuário'),
            ('confirmada', 'Confirmada'),
        ]
    })


def escala_detail_equipe(request, equipe_pk, pk):
    escala = get_object_or_404(Escala, pk=pk)
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    evento_inicio = escala.evento.data_inicio
    evento_fim = escala.evento.data_fim
    evento = escala.evento
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()

    membros = escala.funcao.equipe.membros.filter(aprovado=True)

    # Usuários sem indisponibilidade
    usuarios_sem_indisponibilidade = [
        membro.usuario for membro in membros
        if not Ocupado.objects.filter(
            usuario=membro.usuario,
            data_inicio__lt=evento_fim,
            data_fim__gt=evento_inicio
        ).exists()
    ]

    # Usuários com disponibilidade para o evento
    usuarios_com_disponibilidade = [
        usuario for usuario in usuarios_sem_indisponibilidade
        if Disponivel.objects.filter(
            usuario=usuario,
            data_inicio__lte=evento_inicio,
            data_fim__gte=evento_fim
        ).exists()
    ]

    # Usuários já escalados para o evento
    usuarios_ja_escalados = Escala.objects.filter(
        usuario__in=usuarios_sem_indisponibilidade,
        evento=evento
    ).exclude(pk=escala.pk).select_related('funcao', 'funcao__equipe')

    # Usuários disponíveis e não escalados
    usuarios_disponiveis = [
        usuario for usuario in usuarios_com_disponibilidade
        if not Escala.objects.filter(
            usuario=usuario,
            evento=evento
        ).exclude(pk=escala.pk).exists()
    ]

    return render(request, 'equipe/equipe_escala_detail.html', {
        'escala': escala,
        'equipe': equipe,
        'usuarios_disponiveis': usuarios_disponiveis,
        'usuarios_escalados': usuarios_ja_escalados,
        'is_leader': is_leader,
    })