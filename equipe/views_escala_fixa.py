"""Página do líder para configurar a escala fixa da equipe (regras em escala/fixa.py)."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import formats, timezone

from equipe.decorators import require_lideranca
from escala import fixa
from escala.models import EscalaFixaItem, Funcao
from escalaconnect.regras import RegraDeNegocio

from .models import Equipe

User = get_user_model()

__all__ = ['escala_fixa_equipe']


def _int(valor, padrao=-1):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _dados_da_linha(request, equipe):
    return {
        'dia_semana': _int(request.POST.get('dia_semana')),
        'turno': request.POST.get('turno', ''),
        'semana': _int(request.POST.get('semana')),
        'funcao': get_object_or_404(Funcao, pk=_int(request.POST.get('funcao')), equipe=equipe),
        'usuario': get_object_or_404(User, pk=_int(request.POST.get('usuario'))),
    }


def _avisar_resultado(request, resultado):
    messages.success(request, fixa.descrever_resultado(resultado))
    for pulada in resultado['puladas'][:5]:
        data = formats.date_format(timezone.localtime(pulada['data']), 'D d/m H:i')
        messages.warning(request, f"{pulada['pessoa']} não foi escalado(a) em {pulada['evento']} ({data}): "
                                  f"{pulada['motivo']}. A vaga ficou em aberto.")


@require_lideranca
def escala_fixa_equipe(request, equipe_pk):
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    config = fixa.escala_fixa_da_equipe(equipe)

    if request.method == 'POST':
        acao = request.POST.get('acao')
        try:
            if acao in ('ligar', 'desligar'):
                resultado = fixa.definir_ativa(equipe, acao == 'ligar')
                if acao == 'ligar':
                    messages.info(request, 'Escala fixa ligada: os cultos cadastrados e os próximos serão '
                                           'preenchidos sozinhos.')
                    _avisar_resultado(request, resultado)
                else:
                    messages.info(request, 'Escala fixa desligada: a equipe volta a ser flexível. '
                                           'Os cultos já preenchidos continuam como estão.')
            elif acao == 'adicionar':
                _, resultado = fixa.adicionar_item(equipe, **_dados_da_linha(request, equipe))
                _avisar_resultado(request, resultado)
            elif acao in ('editar', 'excluir'):
                item = get_object_or_404(EscalaFixaItem, pk=_int(request.POST.get('item')), escala_fixa=config)
                if acao == 'editar':
                    resultado = fixa.atualizar_item(item, **_dados_da_linha(request, equipe))
                else:
                    resultado = fixa.excluir_item(item)
                _avisar_resultado(request, resultado)
        except RegraDeNegocio as erro:
            messages.error(request, str(erro))
        return redirect('escala_fixa_equipe', equipe_pk=equipe.pk)

    grupos = {}
    for item in config.itens.select_related('funcao', 'usuario').order_by('dia_semana', 'turno', 'semana',
                                                                           'funcao__nome', 'pk'):
        item.rotulo_semana = fixa.rotulo_da_semana(item.dia_semana, item.semana)
        grupos.setdefault((item.dia_semana, item.turno), []).append(item)
    ordem_turno = [t for t, _ in EscalaFixaItem.TURNOS]
    grupos = [
        {'titulo': fixa.rotulo_do_culto(dia, turno), 'itens': itens}
        for (dia, turno), itens in sorted(grupos.items(), key=lambda g: ((g[0][0] + 1) % 7, ordem_turno.index(g[0][1])))
    ]
    membros = (
        User.objects.filter(membrosequipe__equipe=equipe, membrosequipe__aprovado=True)
        .order_by('first_name', 'last_name', 'username')
    )
    return render(request, 'equipe/escala_fixa.html', {
        'equipe': equipe,
        'config': config,
        'grupos': grupos,
        'funcoes': Funcao.objects.filter(equipe=equipe).order_by('nome'),
        'membros': membros,
        # Domingo primeiro, como no calendário da igreja.
        'dias': [EscalaFixaItem.DIAS[6]] + EscalaFixaItem.DIAS[:6],
        'turnos': EscalaFixaItem.TURNOS,
        'semanas': EscalaFixaItem.SEMANAS,
    })
