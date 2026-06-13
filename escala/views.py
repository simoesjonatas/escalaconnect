from datetime import timezone as datetime_timezone

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from escala.models import Escala, Funcao
from evento.models import Evento
from escala.forms import EscalaForm, MultiEscalaForm, AplicarFuncoesEventosForm
from escala.solicitacao_desistencia_forms import DesistenciaForm
from equipe.decorators import require_lideranca 
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.contrib import messages
from django.conf import settings
from usuario.models import Usuario
from equipe.models import Lideranca, Equipe
from escala.utils import usuarios_disponiveis_para_evento, preencher_vagas


def _user_can_manage_event_functions(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return Lideranca.objects.filter(usuario=user).exists()


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
    evento = escala.evento
    is_leader = Lideranca.objects.filter(usuario=request.user, equipe=escala.funcao.equipe).exists()

    # Parâmetros de busca e ordenação
    order_by = request.GET.get('order_by', 'username')
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    # Usuários disponíveis para o evento: membros aprovados, sem conflito de horário,
    # disponíveis no intervalo e ainda não escalados. Lógica única em escala/utils
    # (elimina o N+1 que existia aqui ao consultar Ocupado/Disponível por membro).
    ids_disponiveis = usuarios_disponiveis_para_evento(
        equipe=escala.funcao.equipe,
        evento=evento,
        excluir_escala_id=escala.pk,
    )
    usuarios_disponiveis = list(Usuario.objects.filter(id__in=ids_disponiveis))

    # Aplica o filtro de busca
    if query:
        usuarios_disponiveis = [
            usuario for usuario in usuarios_disponiveis
            if query.lower() in usuario.username.lower() or
               query.lower() in usuario.first_name.lower() or
               query.lower() in usuario.last_name.lower() or
               query.lower() in usuario.email.lower()
        ]

    # Ordena os usuários
    field = order_by.lstrip('-')
    reverse = order_by.startswith('-')
    usuarios_disponiveis = sorted(
        usuarios_disponiveis,
        key=lambda u: getattr(u, field, '').lower() if isinstance(getattr(u, field, ''), str) else getattr(u, field, ''),
        reverse=reverse
    )

    # Paginação
    paginator = Paginator(usuarios_disponiveis, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    usuario_fields = [
        ('username', 'Nome de Usuário'),
        ('first_name', 'Nome'),
        ('last_name', 'Sobrenome'),
        ('email', 'Email'),
    ]

    return render(request, 'escala/escala_detail.html', {
        'escala': escala,
        'usuarios_disponiveis': page_obj,
        'is_leader': is_leader,
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'usuario_fields': usuario_fields,
        'query': query
    })


@login_required
def minhas_escalas(request):
    # Cards ordenados pela data do evento (a próxima escala primeiro).
    order_by = request.GET.get('order_by', 'evento__data_inicio')
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


@require_lideranca
def multi_escala_create(request, evento_pk):
    evento = get_object_or_404(Evento, pk=evento_pk)

    if request.method == 'POST':
        escalas = request.POST.getlist('escalas')  # Lista de escalas enviadas pelo formulário
        for escala in escalas:
            equipe_id, funcao_id = escala.split(',')
            equipe = get_object_or_404(Equipe, pk=equipe_id)
            funcao = get_object_or_404(Funcao, pk=funcao_id)

            Escala.objects.create(
                evento=evento,
                funcao=funcao,
            )

        return redirect(reverse('evento_escalas', args=[evento.pk]))

    form = MultiEscalaForm()
    return render(request, 'escala/multi_escala_form.html', {'form': form, 'evento': evento})


def carregar_funcoes(request):
    """Retorna funções filtradas por equipe via AJAX."""
    equipe_id = request.GET.get('equipe_id')
    if equipe_id:
        funcoes = Funcao.objects.filter(equipe_id=equipe_id).values('id', 'nome')
        return JsonResponse(list(funcoes), safe=False)
    return JsonResponse([], safe=False)


@login_required
def aplicar_funcoes_eventos(request):
    if not _user_can_manage_event_functions(request.user):
        return render(request, '403_forbidden.html', status=403)

    if request.method == 'POST':
        form = AplicarFuncoesEventosForm(request.POST, user=request.user)
        if form.is_valid():
            eventos = list(form.cleaned_data['eventos'])
            funcoes = list(form.funcoes_selecionadas())
            criadas = 0
            existentes = 0

            with transaction.atomic():
                for evento in eventos:
                    for funcao in funcoes:
                        ja_existe = Escala.objects.filter(evento=evento, funcao=funcao).exists()
                        if ja_existe:
                            existentes += 1
                            continue

                        Escala.objects.create(evento=evento, funcao=funcao)
                        criadas += 1

            if criadas:
                messages.success(
                    request,
                    f"{criadas} função(ões) adicionada(s) aos evento(s) selecionado(s)."
                )
            if existentes:
                messages.info(
                    request,
                    f"{existentes} combinação(ões) já existiam e foram ignoradas para evitar duplicidade."
                )
            if not criadas and not existentes:
                messages.warning(request, "Selecione pelo menos um evento e uma função.")

            return redirect('aplicar_funcoes_eventos')
    else:
        form = AplicarFuncoesEventosForm(user=request.user)

    selected_equipes = {int(value) for value in request.POST.getlist('equipes') if value.isdigit()}
    selected_eventos = {int(value) for value in request.POST.getlist('eventos') if value.isdigit()}
    selected_funcoes = {int(value) for value in request.POST.getlist('funcoes') if value.isdigit()}
    selected_planejamento = request.POST.get('planejamento') or ''

    funcoes_por_equipe = {}
    for funcao in form.fields['funcoes'].queryset:
        funcoes_por_equipe.setdefault(funcao.equipe, []).append(funcao)

    context = {
        'form': form,
        'eventos': form.fields['eventos'].queryset,
        'equipes': form.fields['equipes'].queryset,
        'funcoes_por_equipe': funcoes_por_equipe,
        'selected_equipes': selected_equipes,
        'selected_eventos': selected_eventos,
        'selected_funcoes': selected_funcoes,
        'selected_planejamento': selected_planejamento,
    }
    return render(request, 'escala/aplicar_funcoes_eventos.html', context)


def _ics_escape(text):
    """Escapa caracteres especiais de texto para o formato iCalendar."""
    return (
        (text or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _ics_datetime(dt):
    """Formata um datetime aware em UTC no padrão iCalendar (ex.: 20260611T130000Z)."""
    return dt.astimezone(datetime_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


@login_required
def minha_agenda_ics(request):
    """Exporta as escalas do usuário como arquivo .ics (Google/Apple Calendar).

    Só eventos de hoje para frente — não faz sentido importar escalas passadas.
    """
    escalas = (
        Escala.objects
        .filter(usuario=request.user, evento__data_inicio__gte=now())
        .select_related('evento', 'funcao', 'funcao__equipe')
        .order_by('evento__data_inicio')
    )

    linhas = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Escala Connect//PT-BR//',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:Minhas Escalas',
    ]
    carimbo = _ics_datetime(now())

    for escala in escalas:
        evento = escala.evento
        if not (evento and evento.data_inicio and evento.data_fim):
            continue
        equipe = escala.funcao.equipe.nome if escala.funcao and escala.funcao.equipe else ''
        funcao = escala.funcao.nome if escala.funcao else ''
        titulo = ' - '.join(p for p in (funcao, equipe) if p) or evento.nome
        situacao = 'Confirmada' if escala.confirmada else 'A confirmar'
        linhas += [
            'BEGIN:VEVENT',
            f'UID:escala-{escala.pk}@connect.simoesti.com.br',
            f'DTSTAMP:{carimbo}',
            f'DTSTART:{_ics_datetime(evento.data_inicio)}',
            f'DTEND:{_ics_datetime(evento.data_fim)}',
            f'SUMMARY:{_ics_escape(titulo)}',
            f'DESCRIPTION:{_ics_escape(f"{evento.nome} ({situacao})")}',
            'END:VEVENT',
        ]

    linhas.append('END:VCALENDAR')
    conteudo = '\r\n'.join(linhas) + '\r\n'

    response = HttpResponse(conteudo, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="minhas-escalas.ics"'
    return response


@login_required
def auto_escalar_evento(request, pk):
    """Preenche automaticamente as vagas vazias do evento com voluntários disponíveis.

    Distribui de forma justa, priorizando quem serviu menos nos últimos 60 dias.
    Não mexe em escalas já preenchidas nem confirma presença (isso é do voluntário).
    """
    evento = get_object_or_404(Evento, pk=pk)

    if request.method != 'POST':
        return redirect('evento_escalas', pk=pk)

    # Permissão: staff/superuser ou líder de alguma equipe envolvida no evento.
    is_admin = request.user.is_staff or request.user.is_superuser
    lidera = Lideranca.objects.filter(
        usuario=request.user, equipe__funcao__escala__evento=evento
    ).exists()
    if not (is_admin or lidera):
        return render(request, '403_forbidden.html', status=403)

    vagas = list(
        Escala.objects
        .filter(evento=evento, usuario__isnull=True)
        .select_related('funcao', 'funcao__equipe')
    )

    preenchidas = preencher_vagas(vagas)

    if not vagas:
        messages.info(request, "Não há vagas em aberto neste evento.")
    else:
        if preenchidas:
            messages.success(request, f"{preenchidas} vaga(s) preenchida(s) automaticamente.")
        restantes = len(vagas) - preenchidas
        if restantes:
            messages.warning(request, f"{restantes} vaga(s) sem voluntário disponível no momento.")

    return redirect('evento_escalas', pk=pk)
