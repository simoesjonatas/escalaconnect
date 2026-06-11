from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from evento.models import Evento
from escala.models import Escala
from disponivel.models import Disponivel
from equipe.models import Equipe, MembrosEquipe
from django.db.models import Count
from escalaconnect.tasks import enviar_email_confirmacao_task
from django.utils import timezone
from django.urls import reverse

# View para renderizar a página base
@login_required(login_url='/login/')
def base_view(request):
    tem_disponibilidade = Disponivel.objects.filter(usuario=request.user).exists()
    escalas_pendentes = Escala.objects.filter(
        usuario=request.user,
        confirmada=False,
        evento__data_inicio__gte=timezone.now(),
    ).count()

    # Pedidos de entrada pendentes nas equipes que o usuário lidera (todas, se admin).
    if request.user.is_superuser or request.user.is_staff:
        equipes_lideradas = Equipe.objects.all()
    else:
        equipes_lideradas = Equipe.objects.filter(lideranca__usuario=request.user)

    pendentes = (
        MembrosEquipe.objects
        .filter(equipe__in=equipes_lideradas, aprovado=False)
        .values('equipe_id', 'equipe__nome')
        .annotate(total=Count('id'))
        .order_by('equipe__nome')
    )
    equipes_com_pendentes = [
        {'id': p['equipe_id'], 'nome': p['equipe__nome'], 'total': p['total']}
        for p in pendentes
    ]

    return render(request, 'home/home.html', {
        'tem_disponibilidade': tem_disponibilidade,
        'escalas_pendentes': escalas_pendentes,
        'equipes_com_pendentes': equipes_com_pendentes,
    })

# View para renderizar o calendário
@login_required(login_url='/login/')
def calendario_view(request):
    return render(request, 'calendario.html')

def custom_403(request, exception):
    return render(request, '403_forbidden.html', status=403)

def redirect_to_home(request, exception=None):
    return HttpResponseRedirect('/')

def view_enviar_confirmacao(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)

    escalas = (
        Escala.objects
        .filter(evento=evento, confirmada=False)
        .select_related("usuario", "funcao", "funcao__equipe")
        .exclude(usuario__email__isnull=True)
        .exclude(usuario__email__exact="")
    )

    for escala in escalas:
        enviar_email_confirmacao_task.delay(escala.id)

    if escalas.exists():
        messages.success(request, f"Enfileirados {escalas.count()} e-mails de confirmação.")
    else:
        messages.info(request, "Ninguém pendente de confirmação com e-mail cadastrado.")
    return redirect("evento_detail", pk=evento_id)

def confirmar_presenca(request, evento_id, escala_id):
    escala = get_object_or_404(Escala, pk=escala_id, evento_id=evento_id)
    escala.confirmada = True
    escala.data_confirmacao = timezone.now()
    escala.save(update_fields=["confirmada", "data_confirmacao"])
    messages.success(request, "Presença confirmada – obrigado!")
    return HttpResponseRedirect(reverse("minhas_escalas"))  # ajuste para sua rota de “Minhas Escalas”