from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from escala.models import Escala,Funcao
from evento.models import Evento
from equipe.models import Equipe
from django.db import transaction
from evento.forms_planejamento import PlanejamentoEquipeForm, AplicarPlanejamentoEventosForm
from .forms import EventoComPlanejamentoForm
from planejamento.models import PlanejamentoFuncao
from planejamento.models import Planejamento
from django.contrib import messages
from equipe.decorators import require_lideranca 


def planejamento_equipes(request):
    if request.method == 'POST':
        form = PlanejamentoEquipeForm(request.POST)

        if form.is_valid():
            equipe = form.cleaned_data['equipe']
            eventos = form.cleaned_data['eventos']
            funcoes = form.cleaned_data['funcoes']

            escalas_criadas = []

            for evento in eventos:
                for funcao in funcoes:
                    escala, created = Escala.objects.get_or_create(
                        evento=evento,
                        funcao=funcao,
                        defaults={'confirmada': False, 'data_confirmacao': None}
                    )
                    if created:
                        escalas_criadas.append(escala)

            return redirect('evento_list')

    else:
        form = PlanejamentoEquipeForm()

    return render(request, 'escala/planejamento_equipes.html', {'form': form})

def create_evento_planejamento(request):
    if request.method == 'POST':
        form = EventoComPlanejamentoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                evento = form.save()  # Salva o evento
                planejamento = form.cleaned_data['planejamento']
                
                if planejamento:
                    funcoes = PlanejamentoFuncao.objects.filter(planejamento=planejamento)
                    for pf in funcoes:
                        Escala.objects.create(
                            funcao=pf.funcao,
                            evento=evento,
                        )
                
            return redirect('evento_list')
    else:
        form = EventoComPlanejamentoForm()
    
    return render(request, 'evento/evento_form.html', {'form': form})


@require_lideranca
def aplicar_planejamento_eventos(request, planejamento_id=None):
    if request.method == 'POST':
        form = AplicarPlanejamentoEventosForm(request.POST, planejamento_id=planejamento_id)
        if form.is_valid():
            planejamento = form.cleaned_data['planejamento']
            eventos = form.cleaned_data['eventos']
            funcoes = PlanejamentoFuncao.objects.filter(planejamento=planejamento).select_related('funcao')

            total_criadas = 0
            with transaction.atomic():
                for evento in eventos:
                    for pf in funcoes:
                        _, created = Escala.objects.get_or_create(
                            evento=evento,
                            funcao=pf.funcao,
                            defaults={'confirmada': False, 'data_confirmacao': None}
                        )
                        if created:
                            total_criadas += 1

            messages.success(
                request,
                f"Planejamento aplicado com sucesso. {total_criadas} escala(s) criada(s)."
            )
            return redirect('planejamento_detail', pk=planejamento.pk)
    else:
        form = AplicarPlanejamentoEventosForm(planejamento_id=planejamento_id)

    planejamento = None
    if planejamento_id:
        planejamento = get_object_or_404(Planejamento, pk=planejamento_id)

    return render(
        request,
        'planejamento/planejamento_aplicar_eventos.html',
        {'form': form, 'planejamento': planejamento}
    )