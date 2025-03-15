from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from escala.models import Escala
from evento.models import Evento
from escala.forms import EscalaForm
from escala.solicitacao_desistencia_forms import DesistenciaForm
from equipe.decorators import require_lideranca 
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.contrib import messages
from ocupado.models import Ocupado
from django.conf import settings
from usuario.models import Usuario
from equipe.models import Lideranca


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
    evento = escala.evento
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()

    # Adiciona parâmetros de busca e ordenação
    order_by = request.GET.get('order_by', 'username')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    # pega os membros da equipe e filtra aqueles sem indisponibilidade
    # membros = escala.funcao.equipe.membros.all()
    membros = escala.funcao.equipe.membros.filter(aprovado=True)
    
    # filtra usarios sem indisponibilidades que se sobreponha
    usuarios_filtrados = [membro.usuario for membro in membros if not Ocupado.objects.filter(
        usuario=membro.usuario,
        data_inicio__lt=evento_fim,
        data_fim__gt=evento_inicio
    ).exists()]

    # filtra usuarios que ja estao escalados para o mesmo evento em qualquer funcao
    usuarios_disponiveis = [usuario for usuario in usuarios_filtrados if not Escala.objects.filter(
        usuario=usuario,
        evento=evento
    ).exclude(pk=escala.pk).exists()]  # exclui a escala atual na verificacao
    
    # Aplica o filtro de busca
    if query:
        usuarios_disponiveis = [
            usuario for usuario in usuarios_disponiveis 
            if query.lower() in usuario.username.lower() or 
               query.lower() in usuario.first_name.lower() or 
               query.lower() in usuario.last_name.lower() or 
               query.lower() in usuario.email.lower()
        ]
    
    # Ordena os usuários (convertendo para lista para poder ordenar)
    field = order_by.lstrip('-')
    reverse = order_by.startswith('-')
    
    # Manipulando ordem de forma manual (já que estamos trabalhando com lista, não queryset)
    usuarios_disponiveis = sorted(
        usuarios_disponiveis,
        key=lambda u: getattr(u, field, '').lower() if isinstance(getattr(u, field, ''), str) else getattr(u, field, ''),
        reverse=reverse
    )
    
    # Aplica paginação
    paginator = Paginator(usuarios_disponiveis, 10)  # 10 usuários por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Campos para ordenação da tabela
    usuario_fields = [
        ('username', 'Nome de Usuário'),
        ('first_name', 'Nome'),
        ('last_name', 'Sobrenome'),
        ('email', 'Email'),
    ]
    
    return render(request, 'escala/escala_detail.html', {
        'escala': escala,
        'usuarios_disponiveis': page_obj,  # Agora usamos o objeto de página em vez da lista completa
        'is_leader': is_leader,
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'usuario_fields': usuario_fields,
        'query': query
    })


@login_required
def minhas_escalas(request):
    order_by = request.GET.get('order_by', 'id')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    today = now().date()

    escalas = Escala.objects.filter(
        usuario=request.user,  # filtra apenas escalas do usuario autenticado
        evento__data_inicio__date__gte=today  # filtra eventos que começam hoje ou no futuro
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
    if request.method == 'POST':
        form = DesistenciaForm(request.POST)
        if not form.is_valid():
            # Se o formulário não for válido, renderiza novamente com erros
            return render(request, 'escala/minha_escala_detail.html', {'escala': escala, 'desistencia_form': form})
    else:
        # Se não for uma solicitação POST, simplesmente exibe a página com o formulário vazio
        form = DesistenciaForm(initial={'escala_origem': escala})
        return render(request, 'escala/minha_escala_detail.html', {'escala': escala, 'desistencia_form': form})


@login_required
def escalar_usuario(request, escala_id, usuario_id):
    
    escala = get_object_or_404(Escala, pk=escala_id)
    
    # Verifica se o usuário é líder da equipe, staff ou superusuário
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()
    if request.user.is_staff or request.user.is_superuser or is_leader:
        if not escala.confirmada:
            usuario = get_object_or_404(Usuario, pk=usuario_id)
            escala.usuario = usuario
            escala.save()
            messages.success(request, 'Usuário escalado com sucesso!')
            return redirect('escala_detail', pk=escala_id)
        else:
            messages.error(request, 'A escala já foi confirmada e não pode ser alterada.')
    else:
        messages.error(request, 'Você não tem permissão para realizar esta ação.')
    return redirect('escala_detail', pk=escala_id)

@login_required
def escalar_usuario_equipe(request, escala_id, usuario_id):
    
    escala = get_object_or_404(Escala, pk=escala_id)
    
    # Verifica se o usuário é líder da equipe, staff ou superusuário
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()
    if request.user.is_staff or request.user.is_superuser or is_leader:
        if not escala.confirmada:
            usuario = get_object_or_404(Usuario, pk=usuario_id)
            escala.usuario = usuario
            escala.save()
            messages.success(request, 'Usuário escalado com sucesso!')
            return redirect(reverse('listar_escalas', kwargs={'equipe_pk': escala.equipe.pk}))
        else:
            messages.error(request, 'A escala já foi confirmada e não pode ser alterada.')
    else:
        messages.error(request, 'Você não tem permissão para realizar esta ação.')
    return redirect(reverse('listar_escalas', kwargs={'equipe_pk': escala.equipe.pk}))

@login_required
def cancelar_escala_equipe(request, escala_id):
    escala = get_object_or_404(Escala, pk=escala_id)
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()

    if request.user.is_staff or request.user.is_superuser or is_leader:
        escala.usuario = None
        escala.confirmada = False
        escala.data_confirmacao = None
        escala.save()
        messages.success(request, 'Escala cancelada com sucesso.')
    else:
        messages.error(request, 'Você não tem permissão para cancelar esta escala.')

    return redirect(reverse('listar_escalas', kwargs={'equipe_pk': escala.equipe.pk}))


@login_required
def cancelar_escala(request, escala_id):
    escala = get_object_or_404(Escala, pk=escala_id)
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()

    if request.user.is_staff or request.user.is_superuser or is_leader:
        escala.usuario = None
        escala.confirmada = False
        escala.data_confirmacao = None
        escala.save()
        messages.success(request, 'Escala cancelada com sucesso.')
    else:
        messages.error(request, 'Você não tem permissão para cancelar esta escala.')

    return redirect('escala_detail', pk=escala_id)

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