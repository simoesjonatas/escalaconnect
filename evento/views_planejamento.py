from django.shortcuts import render, redirect
from django.utils.timezone import now
from escala.models import Escala,Funcao
from evento.models import Evento
from equipe.models import Equipe
from evento.forms_planejamento import PlanejamentoEquipeForm

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
