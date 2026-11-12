"""Site do líder: dias que a pessoa escolheu (disponibilidade e ofertas) e escalar num deles.

Mesma regra da tela do app (escala.services.escolhas_da_pessoa). Escalar passa por
escala.services.escalar_em_vaga: a pessoa recebe "Você foi escalado" e as outras ofertas
daquela vaga se encerram pelos signals.
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from equipe import services as equipe_services
from equipe.decorators import require_lideranca
from equipe.models import Equipe
from escala import services as escala_services
from escala.models import Escala
from escala.utils import _ano_mes_local
from escalaconnect.regras import RegraDeNegocio


def _pessoa_e_equipes(request, equipe_pk, usuario_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    pessoa = get_object_or_404(get_user_model(), pk=usuario_pk, is_active=True)
    equipes = list(equipe_services.equipes_em_comum(request.user, pessoa))
    if equipe not in equipes:
        raise Http404
    return equipe, pessoa, equipes


@require_lideranca
@require_http_methods(['GET', 'POST'])
def escolhas_da_pessoa(request, equipe_pk, usuario_pk):
    equipe, pessoa, equipes = _pessoa_e_equipes(request, equipe_pk, usuario_pk)
    nome = pessoa.get_full_name() or pessoa.username

    if request.method == 'POST':
        vaga = get_object_or_404(
            Escala.objects.select_related('evento', 'funcao__equipe'),
            pk=request.POST.get('vaga') or 0, usuario__isnull=True, funcao__equipe__in=equipes,
        )
        try:
            escala_services.escalar_em_vaga(vaga, pessoa, mesmo_evento=bool(request.POST.get('mesmo_evento')))
        except RegraDeNegocio as erro:
            messages.error(request, str(erro))
        else:
            messages.success(
                request,
                f'{nome} foi escalado em {vaga.funcao.nome} · {vaga.evento.nome} '
                f'({timezone.localtime(vaga.evento.data_inicio):%d/%m %H:%M}) e recebeu o aviso.',
            )
        return redirect('escolhas_da_pessoa', equipe_pk=equipe.pk, usuario_pk=pessoa.pk)

    ano, mes = _ano_mes_local(timezone.now())
    return render(request, 'equipe/escolhas_pessoa.html', {
        'equipe': equipe,
        'pessoa': pessoa,
        'nome': nome,
        'equipes': equipes,
        'servicos_no_mes': Escala.objects.filter(
            usuario=pessoa, evento__data_inicio__year=ano, evento__data_inicio__month=mes).count(),
        'escolhas': escala_services.escolhas_da_pessoa(pessoa, equipes),
    })
