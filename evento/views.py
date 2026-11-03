from django.http import JsonResponse
from .models import Evento
from .services import feed_calendario
from .services import gerar_eventos_em_massa as gerar_eventos_em_massa_service
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Count, Q
from escala.models import Escala
from escala.utils import anotar_disponiveis, escalas_com_situacao, resumo_das_escalas
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
from escalaconnect.notificacoes import pedir_confirmacao
from django.contrib import messages



def eventos_api(request):
    # Eventos visíveis, filtros e escalas do usuário: evento/services.py (compartilhado com a API do app).
    eventos = feed_calendario(
        request.user,
        filtro=request.GET.get('filtro', ''),
        equipe=request.GET.get('equipe', ''),
    )

    data = []
    for evento, mine in eventos:
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

    # Prévia das escalas de cada evento, numa consulta só (antes: has_issues por linha).
    vaga = Q(escala__usuario__isnull=True)
    eventos = eventos.select_related('equipe').annotate(
        funcoes=Count('escala', distinct=True),
        confirmadas=Count('escala', filter=Q(escala__usuario__isnull=False, escala__confirmada=True), distinct=True),
        vagas=Count('escala', filter=vaga, distinct=True),
        querem_servir=Count('escala__rendimento', filter=vaga & Q(escala__rendimento__aprovada=False), distinct=True),
        pendencias=(
            Count('escala__desistencia', filter=Q(escala__desistencia__aprovada=False), distinct=True)
            + Count('escala__solicitacoes_origem', filter=Q(escala__solicitacoes_origem__aprovada=False), distinct=True)
        ),
    ).order_by(order_by, 'pk')

    # Equipes oferecidas no filtro: as que o usuário lidera (admin vê todas).
    if request.user.is_superuser or request.user.is_staff:
        equipes_filtro = Equipe.objects.all().order_by('nome')
    else:
        equipes_filtro = Equipe.objects.filter(lideranca__usuario=request.user).order_by('nome')

    paginator = Paginator(eventos, 10)  # Exibe 10 eventos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    fields = [
        ('nome', 'Evento'),
        ('data_inicio', 'Quando'),
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
            funcoes = list(form.cleaned_data['funcoes'])
            eventos, ignorados = gerar_eventos_em_massa_service(
                nome=form.cleaned_data['nome'],
                equipe=form.cleaned_data['equipe'],
                meses=meses,
                dias_da_semana=form.cleaned_data['dias_da_semana'],
                horario_inicio=form.cleaned_data['horario_inicio'],
                horario_fim=form.cleaned_data['horario_fim'],
                observacao=form.cleaned_data['observacao'],
                funcoes=funcoes,
            )

            vagas = f" com {len(funcoes)} vaga(s) cada" if funcoes and eventos else ""
            messages.success(
                request,
                f"{len(eventos)} evento(s) criado(s){vagas}. "
                f"{ignorados} data(s) passada(s) ou já existente(s) ignorada(s).",
            )
            return redirect('evento_list')
    else:
        form = GerarEventosEmMassaForm(user=request.user)

    return render(request, 'evento/gerar_eventos_em_massa.html', {
        'form': form,
        'funcoes': form.fields['funcoes'].queryset,
        'funcoes_marcadas': [str(v) for v in (form['funcoes'].value() or [])],
    })

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
    # Funções do evento por equipe, com a situação e a prévia de quem pode servir.
    todas = Escala.objects.filter(evento=evento)
    escalas = list(escalas_com_situacao(todas).order_by('funcao__equipe__nome', 'funcao__nome', 'pk'))
    anotar_disponiveis(escalas, evento)
    return render(request, 'evento/evento_detail.html', {
        'evento': evento,
        'pode_gerenciar': pode_gerenciar,
        'escalas': escalas,
        'resumo': resumo_das_escalas(todas),
    })

@login_required(login_url='/login/')
def view_enviar_confirmacao(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_ser_gerenciada_por(request.user):
        return render(request, '403_forbidden.html', status=403)

    # E-mail para quem tem e-mail e push para quem tem o app.
    total = pedir_confirmacao(evento)

    if total:
        messages.success(request, f"{total} e-mail(s) de confirmação publicado(s) para envio.")
    else:
        messages.info(request, "Ninguém pendente de confirmação com e-mail cadastrado.")

    return redirect('evento_detail', pk=evento_id)

@login_required(login_url='/login/')
def view_enviar_lembrete(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_ser_gerenciada_por(request.user):
        return render(request, '403_forbidden.html', status=403)

    total = pedir_confirmacao(evento, lembrete=True)

    if total:
        messages.success(request, f"{total} lembrete(s) de escala publicado(s) para envio.")
    else:
        messages.info(request, "Ninguém pendente de lembrete com e-mail cadastrado.")
    return redirect('evento_detail', pk=evento_id)
