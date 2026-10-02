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
