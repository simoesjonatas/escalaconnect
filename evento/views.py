from django.http import JsonResponse
from .models import Evento
from django.views.decorators.csrf import csrf_exempt
import json
from escala.models import Escala
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .forms import EventoForm
from .forms import GerarEventosEmMassaForm
from escalaconnect.utils import admin_required
from equipe.decorators import require_lideranca, require_lider_ou_staff
from equipe.models import Equipe
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from escalaconnect.tasks import enviar_email_confirmacao_task
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import date, datetime
import calendar



def eventos_api(request):
    eventos = Evento.objects.visiveis_para(request.user).order_by('data_inicio')

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
    equipe_filtro = request.GET.get('equipe', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    today = now().date()

    eventos = Evento.objects.visiveis_para(request.user).filter(
        data_inicio__date__gte=today,
        nome__icontains=query)

    # Filtro por equipe: uma equipe específica ou apenas os eventos públicos.
    if equipe_filtro == 'publicos':
        eventos = eventos.filter(equipe__isnull=True)
    elif equipe_filtro:
        eventos = eventos.filter(equipe_id=equipe_filtro)

    eventos = eventos.order_by(order_by)

    # Equipes oferecidas no filtro: as que o usuário lidera (admin vê todas).
    if request.user.is_superuser or request.user.is_staff:
        equipes_filtro = Equipe.objects.all().order_by('nome')
    else:
        equipes_filtro = Equipe.objects.filter(lideranca__usuario=request.user).order_by('nome')

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
        'equipes_filtro': equipes_filtro,
        'equipe_filtro': equipe_filtro,
    }
    return render(request, 'evento/evento_list.html', context)

@require_lider_ou_staff
def evento_create(request):
    if request.method == 'POST':
        form = EventoForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('evento_list')
    else:
        form = EventoForm(user=request.user)
    return render(request, 'evento/evento_form.html', {'form': form})


@require_lider_ou_staff
def gerar_eventos_em_massa(request):
    if request.method == 'POST':
        form = GerarEventosEmMassaForm(request.POST, user=request.user)
        if form.is_valid():
            mes_escolhido = form.cleaned_data['mes']
            if mes_escolhido == 'ambos':
                meses = [valor for valor, _ in form.fields['mes'].choices if valor != 'ambos']
            else:
                meses = [mes_escolhido]
            dias_escolhidos = {int(dia) for dia in form.cleaned_data['dias_da_semana']}
            horario_inicio = form.cleaned_data['horario_inicio']
            horario_fim = form.cleaned_data['horario_fim']
            equipe = form.cleaned_data['equipe']
            agora = timezone.now()
            eventos = []
            ignorados = 0

            for valor_mes in meses:
                ano, mes = map(int, valor_mes.split('-'))
                for numero_dia in range(1, calendar.monthrange(ano, mes)[1] + 1):
                    data_evento = date(ano, mes, numero_dia)
                    if data_evento.weekday() not in dias_escolhidos:
                        continue

                    inicio = timezone.make_aware(datetime.combine(data_evento, horario_inicio))
                    fim = timezone.make_aware(datetime.combine(data_evento, horario_fim))
                    if inicio <= agora or Evento.objects.filter(
                        nome=form.cleaned_data['nome'],
                        equipe=equipe,
                        data_inicio=inicio,
                    ).exists():
                        ignorados += 1
                        continue

                    eventos.append(Evento(
                        nome=form.cleaned_data['nome'],
                        equipe=equipe,
                        data_inicio=inicio,
                        data_fim=fim,
                        observacao=form.cleaned_data['observacao'],
                    ))

            with transaction.atomic():
                Evento.objects.bulk_create(eventos)

            messages.success(
                request,
                f"{len(eventos)} evento(s) criado(s). {ignorados} data(s) passada(s) ou já existente(s) ignorada(s).",
            )
            return redirect('evento_list')
    else:
        form = GerarEventosEmMassaForm(user=request.user)

    return render(request, 'evento/gerar_eventos_em_massa.html', {'form': form})

@login_required
def evento_update(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if not evento.pode_ser_gerenciada_por(request.user):
        return render(request, '403_forbidden.html', status=403)
    if request.method == 'POST':
        form = EventoForm(request.POST, instance=evento, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('evento_list')
    else:
        form = EventoForm(instance=evento, user=request.user)
    return render(request, 'evento/evento_form.html', {'form': form})

@login_required
def evento_delete(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if not evento.pode_ser_gerenciada_por(request.user):
        return render(request, '403_forbidden.html', status=403)
    if request.method == 'POST':
        evento.delete()
        return redirect('evento_list')
    return render(request, 'evento/evento_confirm_delete.html', {'evento': evento})

def evento_detail(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    pode_gerenciar = request.user.is_authenticated and evento.pode_ser_gerenciada_por(request.user)
    return render(request, 'evento/evento_detail.html', {
        'evento': evento,
        'pode_gerenciar': pode_gerenciar,
    })

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
