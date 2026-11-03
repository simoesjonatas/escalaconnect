import calendar
from datetime import date, datetime

from django.db import transaction
from django.utils import timezone

from escala.models import Escala

from .models import Evento


def feed_calendario(usuario, filtro='', equipe='', inicio=None, fim=None):
    """Eventos do calendário do usuário, cada um com o resumo das escalas dele.

    Devolve uma lista de (evento, minha), em que `minha` é None ou
    {'confirmada': bool, 'funcoes': [nomes]}. Usado pelo site (FullCalendar) e
    pela API do app. `inicio`/`fim` limitam a janela de datas.
    """
    eventos = Evento.objects.visiveis_para(usuario).select_related('equipe').order_by('data_inicio')

    # Filtros do calendário: só minhas escalas, só públicos ou uma equipe específica.
    # A equipe é aplicada sobre visiveis_para, então não expõe eventos de equipes alheias.
    equipe = str(equipe or '')
    if filtro == 'escalado' and usuario.is_authenticated:
        eventos = eventos.filter(escala__usuario=usuario).distinct()
    elif equipe == 'publicos':
        eventos = eventos.filter(equipe__isnull=True)
    elif equipe.isdigit():
        eventos = eventos.filter(equipe_id=equipe)

    if inicio is not None:
        eventos = eventos.filter(data_fim__gte=inicio)
    if fim is not None:
        eventos = eventos.filter(data_inicio__lte=fim)

    # Escalas do usuário, para destacar no calendário as próprias escalas.
    minhas = {}
    if usuario.is_authenticated:
        for esc in Escala.objects.filter(usuario=usuario).select_related('funcao'):
            info = minhas.setdefault(esc.evento_id, {'confirmada': True, 'funcoes': []})
            if esc.funcao:
                info['funcoes'].append(esc.funcao.nome)
            if not esc.confirmada:
                info['confirmada'] = False

    return [(evento, minhas.get(evento.id)) for evento in eventos]


# ── Criar eventos (site e app do líder usam as mesmas regras) ──

def criar_evento(nome, equipe, data_inicio, data_fim, observacao='', funcoes=()):
    """Cria um evento e uma vaga (escala sem voluntário) por função; ninguém é avisado agora."""
    with transaction.atomic():
        evento = Evento.objects.create(
            nome=nome, equipe=equipe, data_inicio=data_inicio, data_fim=data_fim, observacao=observacao or '')
        Escala.objects.bulk_create([Escala(evento=evento, funcao=funcao) for funcao in funcoes])
    return evento


def gerar_eventos_em_massa(nome, equipe, meses, dias_da_semana, horario_inicio, horario_fim,
                           observacao='', funcoes=()):
    """Um evento em cada dia escolhido (0 = segunda) dos meses ('AAAA-MM'), com uma vaga por função.

    Pula datas passadas e eventos que já existem (mesmo nome, equipe e início).
    Devolve (eventos criados, quantas datas foram ignoradas).
    """
    agora = timezone.now()
    dias_da_semana = {int(dia) for dia in dias_da_semana}
    eventos, ignorados = [], 0
    for valor_mes in meses:
        ano, mes = map(int, valor_mes.split('-'))
        for numero_dia in range(1, calendar.monthrange(ano, mes)[1] + 1):
            data_evento = date(ano, mes, numero_dia)
            if data_evento.weekday() not in dias_da_semana:
                continue
            inicio = timezone.make_aware(datetime.combine(data_evento, horario_inicio))
            fim = timezone.make_aware(datetime.combine(data_evento, horario_fim))
            if inicio <= agora or Evento.objects.filter(nome=nome, equipe=equipe, data_inicio=inicio).exists():
                ignorados += 1
                continue
            eventos.append(Evento(nome=nome, equipe=equipe, data_inicio=inicio, data_fim=fim,
                                  observacao=observacao or ''))

    funcoes = list(funcoes)
    with transaction.atomic():
        for evento in eventos:
            evento.save()
        # Uma vaga por função em cada evento; sem voluntário, então ninguém é avisado agora.
        Escala.objects.bulk_create([Escala(evento=evento, funcao=funcao) for evento in eventos for funcao in funcoes])
    return eventos, ignorados


def aplicar_funcoes(eventos, funcoes):
    """Cria uma vaga de cada função em cada evento, pulando as que já existem.

    Devolve (vagas criadas, combinações que já existiam).
    """
    funcoes = list(funcoes)
    criadas = existentes = 0
    with transaction.atomic():
        for evento in eventos:
            ja_tem = set(Escala.objects.filter(evento=evento, funcao__in=funcoes).values_list('funcao_id', flat=True))
            novas = [Escala(evento=evento, funcao=f) for f in funcoes if f.pk not in ja_tem]
            Escala.objects.bulk_create(novas)
            criadas += len(novas)
            existentes += len(ja_tem)
    return criadas, existentes
