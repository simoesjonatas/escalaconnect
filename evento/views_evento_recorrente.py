from django.shortcuts import render, redirect
from django.utils.timezone import make_aware
from datetime import timedelta, datetime
from evento.models import Evento
from escala.models import Escala
from escala.models import Funcao
from evento.forms_evento_recorrente import GeradorEventosPlanejamentoForm

def gerar_eventos_planejamento(request):
    if request.method == 'POST':
        form = GeradorEventosPlanejamentoForm(request.POST)

        if form.is_valid():
            nome_evento = form.cleaned_data['nome_evento']
            horario_inicio = form.cleaned_data['horario_inicio']
            horario_fim = form.cleaned_data['horario_fim']
            dia_semana = int(form.cleaned_data['dia_semana'])
            duracao_meses = form.cleaned_data['duracao_meses']
            equipe = form.cleaned_data['equipe']
            funcoes = form.cleaned_data['funcoes']

            data_atual = datetime.now().date()
            data_futura = data_atual + timedelta(weeks=4 * duracao_meses)

            eventos_criados = []
            escalas_criadas = []

            while data_atual <= data_futura:
                if data_atual.weekday() == dia_semana:
                    evento = Evento.objects.create(
                        nome=f"{nome_evento} - {data_atual.strftime('%d/%m/%Y')}",
                        data_inicio=make_aware(datetime.combine(data_atual, horario_inicio)),
                        data_fim=make_aware(datetime.combine(data_atual, horario_fim))
                    )
                    eventos_criados.append(evento)

                    # Criar escalas para cada função escolhida
                    for funcao in funcoes:
                        escala = Escala.objects.create(
                            evento=evento,
                            funcao=funcao,
                            confirmada=False
                        )
                        escalas_criadas.append(escala)

                data_atual += timedelta(days=1)

            return redirect('evento_list')

    else:
        form = GeradorEventosPlanejamentoForm()

    return render(request, 'escala/gerador_eventos_planejamento.html', {'form': form})
