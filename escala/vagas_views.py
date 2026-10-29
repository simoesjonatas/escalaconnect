"""Vagas em aberto para o voluntário no site (mesma regra da tela do app)."""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from equipe.decorators import pode_gerenciar_equipe

from . import services
from .models import Escala, Rendimento

POR_PAGINA = 15
# Parâmetros da lista que os botões de oferecer/desistir preservam ao voltar.
PARAMETROS_DA_LISTA = ('equipe', 'quando', 'page')


def equipes_das_vagas(vagas):
    """[(id, nome, total)] das equipes que têm vaga, para o filtro (só equipes com opção)."""
    equipes = {}
    for vaga in vagas:
        equipe = vaga.funcao.equipe
        equipes.setdefault(equipe.pk, [equipe.pk, equipe.nome, 0])[2] += 1
    return sorted((tuple(e) for e in equipes.values()), key=lambda e: e[1].lower())


def periodos():
    """Esta semana (segunda a domingo), a próxima, este mês e o próximo: (valor, rótulo, início, fim exclusivo)."""
    hoje = timezone.localdate()
    segunda = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)
    proximo_mes = (inicio_mes + timedelta(days=32)).replace(day=1)
    depois = (proximo_mes + timedelta(days=32)).replace(day=1)
    return [
        ('semana', 'Esta semana', segunda, segunda + timedelta(days=7)),
        ('proxima-semana', 'Próxima semana', segunda + timedelta(days=7), segunda + timedelta(days=14)),
        ('mes', 'Este mês', inicio_mes, proximo_mes),
        ('proximo-mes', 'Próximo mês', proximo_mes, depois),
    ]


def _no_periodo(vaga, inicio, fim):
    return inicio <= timezone.localdate(vaga.evento.data_inicio) < fim


@login_required
def vagas_abertas(request):
    todas = services.vagas_visiveis_para(request.user)
    equipes = equipes_das_vagas(todas)
    equipe_id = request.GET.get('equipe')
    if len(equipes) > 1 and equipe_id and equipe_id.isdigit() and any(e[0] == int(equipe_id) for e in equipes):
        equipe_id = int(equipe_id)
        vagas = [v for v in todas if v.funcao.equipe_id == equipe_id]
    else:
        equipe_id, vagas = None, todas

    # Como no app: só entra o período que separa parte da lista (nem nenhuma vaga, nem todas).
    opcoes_de_periodo = []
    for valor, rotulo, inicio, fim in periodos():
        quantas = sum(_no_periodo(v, inicio, fim) for v in vagas)
        if 0 < quantas < len(vagas):
            opcoes_de_periodo.append((valor, rotulo, inicio, fim))
    quando = next((p for p in opcoes_de_periodo if p[0] == request.GET.get('quando')), None)
    if quando:
        vagas = [v for v in vagas if _no_periodo(v, quando[2], quando[3])]

    return render(request, 'escala/vagas_abertas.html', {
        'page_obj': Paginator(vagas, POR_PAGINA).get_page(request.GET.get('page')),
        'total': len(todas),
        'mostrando': len(vagas),
        'filtrando': bool(equipe_id or quando),
        'equipes': equipes,
        'equipe_id': equipe_id,
        'periodos': [(valor, rotulo) for valor, rotulo, _, _ in opcoes_de_periodo],
        'quando': quando[0] if quando else None,
    })


def _voltar(request):
    """Volta para a lista na mesma página e com os mesmos filtros (ou para Minhas Disponibilidades)."""
    if request.POST.get('origem') == 'disponibilidade':
        return redirect('lista_disponivel')
    url = redirect('vagas_abertas')
    anteriores = QueryDict(request.POST.get('voltar', ''))
    params = QueryDict(mutable=True)
    for chave in PARAMETROS_DA_LISTA:
        if anteriores.get(chave):
            params[chave] = anteriores[chave]
    if params:
        url['Location'] += f'?{params.urlencode()}'
    return url


@login_required
def oferecer_para_vaga(request, pk):
    if request.method == 'POST':
        try:
            services.oferecer_para_vaga(get_object_or_404(Escala, pk=pk), request.user)
            messages.success(request, 'Oferta enviada! A liderança vai confirmar e você recebe um aviso.')
        except services.RegraDeNegocio as erro:
            messages.error(request, str(erro))
    return _voltar(request)


@login_required
def desistir_da_vaga(request, pk):
    if request.method == 'POST':
        try:
            services.cancelar_oferta(get_object_or_404(Escala, pk=pk), request.user)
            messages.success(request, 'Oferta retirada.')
        except services.RegraDeNegocio as erro:
            messages.error(request, str(erro))
    return _voltar(request)


@login_required
def recusar_oferta(request, pk):
    """Líder descarta a oferta de alguém para a vaga (sem aviso, como no app)."""
    oferta = get_object_or_404(Rendimento.objects.select_related('escala__funcao__equipe', 'candidato'),
                               pk=pk, aprovada=False)
    escala = oferta.escala
    if request.method == 'POST':
        if pode_gerenciar_equipe(request.user, escala.equipe):
            services.recusar_oferta(oferta)
            nome = oferta.candidato.get_full_name() or oferta.candidato.username
            messages.success(request, f'Oferta de {nome} recusada.')
        else:
            messages.error(request, 'Você não tem permissão para realizar esta ação.')
    return redirect('escala_detail_equipe', equipe_pk=escala.equipe.pk, pk=escala.pk)
