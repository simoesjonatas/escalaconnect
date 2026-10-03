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
from escalaconnect.services import pendencias_home
from escalaconnect.notificacoes import pedir_confirmacao
from escalaconnect.confirmacao import usuario_do_token
from escalaconnect.regras import RegraDeNegocio
from escala.services import confirmar_escala
from django.contrib.auth.views import redirect_to_login
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

# View para renderizar a página base
@login_required(login_url='/login/')
def base_view(request):
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
        # Pendências do voluntário (as mesmas que a API do app devolve em /home/).
        **pendencias_home(request.user),
        'equipes_com_pendentes': equipes_com_pendentes,
    })

# View para renderizar o calendário
@login_required(login_url='/login/')
def calendario_view(request):
    # Equipes oferecidas no filtro do calendário: as do usuário (admin vê todas).
    if request.user.is_superuser or request.user.is_staff:
        minhas_equipes = Equipe.objects.all().order_by('nome')
    else:
        from equipe.models import Lideranca
        equipe_ids = set(
            MembrosEquipe.objects.filter(usuario=request.user, aprovado=True)
            .values_list('equipe_id', flat=True)
        )
        equipe_ids |= set(
            Lideranca.objects.filter(usuario=request.user).values_list('equipe_id', flat=True)
        )
        minhas_equipes = Equipe.objects.filter(id__in=equipe_ids).order_by('nome')
    return render(request, 'calendario.html', {'minhas_equipes': minhas_equipes})

def privacidade(request):
    """Política de privacidade, pública (a Play Store exige um endereço fixo)."""
    return render(request, 'privacidade.html', {'contato': settings.PRIVACIDADE_CONTATO})

def custom_403(request, exception):
    return render(request, '403_forbidden.html', status=403)

def redirect_to_home(request, exception=None):
    return HttpResponseRedirect('/')

@login_required(login_url='/login/')
def view_enviar_confirmacao(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_ser_gerenciada_por(request.user):
        return render(request, '403_forbidden.html', status=403)

    total = pedir_confirmacao(evento)
    if total:
        messages.success(request, f"Enfileirados {total} e-mails de confirmação.")
    else:
        messages.info(request, "Ninguém pendente de confirmação com e-mail cadastrado.")
    return redirect("evento_detail", pk=evento_id)

def confirmar_presenca(request, evento_id, escala_id):
    """Confirmação pelo link do e-mail, sem exigir login.

    O link leva um token assinado (escalaconnect/confirmacao.py) que só vale para
    aquela escala e aquele voluntário. Sem token válido, só confirma se quem está
    logado é o dono da escala; caso contrário, manda para o login.
    """
    escala = get_object_or_404(Escala, pk=escala_id, evento_id=evento_id)
    usuario_id = usuario_do_token(request.GET.get('t', ''), escala)
    if usuario_id is None and request.user.is_authenticated:
        usuario_id = request.user.pk
    if usuario_id is None or escala.usuario_id != usuario_id:
        messages.error(request, "Entre na sua conta para confirmar esta escala.")
        return redirect_to_login(reverse("minhas_escalas"), login_url='/login/')

    try:
        confirmar_escala(escala, escala.usuario)
        messages.success(request, "Presença confirmada – obrigado!")
    except RegraDeNegocio as erro:
        (messages.info if erro.code == 'ja_confirmada' else messages.error)(request, str(erro))
    return HttpResponseRedirect(reverse("minhas_escalas"))