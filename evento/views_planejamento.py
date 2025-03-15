from django.shortcuts import render, redirect
from django.utils.timezone import now
from escala.models import Escala,Funcao
from evento.models import Evento
from equipe.models import Equipe
from django.db import transaction
from evento.forms_planejamento import PlanejamentoEquipeForm
from .forms import EventoComPlanejamentoForm
from planejamento.models import PlanejamentoFuncao

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