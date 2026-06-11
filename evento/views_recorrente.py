from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import timedelta, datetime, date, time
import calendar
from .models import Evento
from .forms import EventoRecorrenteForm, GerarCultosMensaisForm
from planejamento.models import Planejamento, PlanejamentoFuncao
from escala.models import Escala
from escalaconnect.utils import admin_required


def _proximo_mes(ano, mes):
    if mes == 12:
        return ano + 1, 1
    return ano, mes + 1


def _datas_do_mes_por_dia_semana(ano, mes, dia_semana):
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    for dia in range(1, ultimo_dia + 1):
        data = date(ano, mes, dia)
        if data.weekday() == dia_semana:
            yield data


def _criar_evento_culto(nome, data_evento, horario_inicio, horario_fim, ignorar_existentes=True):
    data_inicio = timezone.make_aware(datetime.combine(data_evento, horario_inicio))
    data_fim = timezone.make_aware(datetime.combine(data_evento, horario_fim))

    if ignorar_existentes and Evento.objects.filter(
        nome=nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
    ).exists():
        return None

    return Evento.objects.create(
        nome=nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


def gerar_cultos_mensais(ano, mes, quantidade_meses, ignorar_existentes=True):
    eventos_criados = []
    eventos_pulados = 0

    for _ in range(quantidade_meses):
        for data_domingo in _datas_do_mes_por_dia_semana(ano, mes, 6):
            for nome, inicio, fim in (
                ("Culto de Domingo - Manhã", time(9, 45), time(12, 0)),
                ("Culto de Domingo - Noite", time(18, 0), time(21, 0)),
            ):
                evento = _criar_evento_culto(nome, data_domingo, inicio, fim, ignorar_existentes)
                if evento:
                    eventos_criados.append(evento)
                else:
                    eventos_pulados += 1

        for data_quarta in _datas_do_mes_por_dia_semana(ano, mes, 2):
            evento = _criar_evento_culto(
                "Culto de Quarta-feira",
                data_quarta,
                time(19, 30),
                time(21, 0),
                ignorar_existentes,
            )
            if evento:
                eventos_criados.append(evento)
            else:
                eventos_pulados += 1

        ano, mes = _proximo_mes(ano, mes)

    return eventos_criados, eventos_pulados



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
            
            # add apartir de qual data para nao sobrescrever os outros eventos
            data_inicial = form.cleaned_data.get('data_inicial')
            # Caso não informe data_inicial, usar data atual
            data_atual = data_inicial if data_inicial else timezone.now().date()

            # data_atual = timezone.now().date()

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


@admin_required
def gerar_cultos_mensais_view(request):
    if request.method == 'POST':
        form = GerarCultosMensaisForm(request.POST)
        if form.is_valid():
            eventos_criados, eventos_pulados = gerar_cultos_mensais(
                ano=form.cleaned_data['ano'],
                mes=form.cleaned_data['mes'],
                quantidade_meses=form.cleaned_data['quantidade_meses'],
                ignorar_existentes=form.cleaned_data['ignorar_existentes'],
            )
            messages.success(
                request,
                f"{len(eventos_criados)} eventos criados. {eventos_pulados} eventos já existentes ignorados."
            )
            return redirect('evento_list')
    else:
        form = GerarCultosMensaisForm()

    return render(request, 'evento/gerar_cultos_mensais.html', {'form': form})
