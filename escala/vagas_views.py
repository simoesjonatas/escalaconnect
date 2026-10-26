"""Vagas em aberto para o voluntário no site (mesma regra da tela do app)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .models import Escala


def equipes_das_vagas(vagas):
    """[(id, nome, total)] das equipes que têm vaga, para o filtro (só equipes com opção)."""
    equipes = {}
    for vaga in vagas:
        equipe = vaga.funcao.equipe
        equipes.setdefault(equipe.pk, [equipe.pk, equipe.nome, 0])[2] += 1
    return sorted((tuple(e) for e in equipes.values()), key=lambda e: e[1].lower())


@login_required
def vagas_abertas(request):
    vagas = services.vagas_visiveis_para(request.user)
    equipes = equipes_das_vagas(vagas)
    equipe_id = request.GET.get('equipe')
    if equipe_id and equipe_id.isdigit() and any(e[0] == int(equipe_id) for e in equipes):
        vagas = [v for v in vagas if v.funcao.equipe_id == int(equipe_id)]
        equipe_id = int(equipe_id)
    else:
        equipe_id = None
    return render(request, 'escala/vagas_abertas.html', {
        'vagas': vagas,
        'equipes': equipes,
        'equipe_id': equipe_id,
    })


def _voltar(request):
    destino = request.POST.get('equipe')
    url = redirect('vagas_abertas')
    if destino and destino.isdigit():
        url['Location'] += f'?equipe={destino}'
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
