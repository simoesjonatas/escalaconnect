from django.utils import timezone
from django.shortcuts import render, redirect
from datetime import timedelta, datetime
from .models import Evento
from .forms import EventoRecorrenteForm
from planejamento.models import Planejamento, PlanejamentoFuncao
from escala.models import Escala



def evento_create_recorrente(request):
    if request.method == 'POST':
        form = EventoRecorrenteForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            horario_inicio = form.cleaned_data['data_inicio']
            horario_fim = form.cleaned_data['data_fim']
            dia_da_semana = int(form.cleaned_data['dia_da_semana'])
            repeticoes = form.cleaned_data['repeticoes']
            planejamento = form.cleaned_data['planejamento']

            data_atual = timezone.now().date()

            eventos_criados = []
            count = 0

            while count < repeticoes:
                # Encontra a próxima data correspondente ao dia da semana escolhido
                while data_atual.weekday() != dia_da_semana:
                    data_atual += timedelta(days=1)

                # Criando evento com timezone definido
                evento = Evento.objects.create(
                    nome=nome,
                    data_inicio=timezone.make_aware(datetime.combine(data_atual, horario_inicio)),
                    data_fim=timezone.make_aware(datetime.combine(data_atual, horario_fim)),
                )
                eventos_criados.append(evento)
                
                
                # Criar Escalas com base no Planejamento selecionado
                for planejamento_funcao in PlanejamentoFuncao.objects.filter(planejamento=planejamento):
                    Escala.objects.create(
                        evento=evento,
                        funcao=planejamento_funcao.funcao,
                        confirmada=False
                    )

                # Avança para a próxima semana
                data_atual += timedelta(weeks=1)
                count += 1

            return redirect('evento_list')  # Redireciona para a lista de eventos

    else:
        form = EventoRecorrenteForm()

    return render(request, 'evento/evento_create_recorrente.html', {'form': form})
