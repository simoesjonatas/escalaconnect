"""Escala fixa: a equipe repete a mesma escala todo mês e o sistema preenche os cultos sozinho.

Cada linha (EscalaFixaItem) diz em qual culto a pessoa serve: dia da semana + turno + semana do
mês ("toda semana" ou 1º a 5º). Num culto, em cada função, valem as linhas daquela semana; sem
nenhuma para aquela função, valem as de "toda semana".

A escala preenchida é uma escala normal (confirmar, lembretes, impedimento, troca). Ela guarda a
linha que a gerou (`item_fixo`), e por isso nunca é preenchida de novo: a troca feita pelo líder e
o impedimento aprovado continuam valendo. Site, API do app, sinal de evento novo e tarefa diária
usam estas funções.
"""
import logging
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from equipe.models import MembrosEquipe
from escalaconnect import mensagens_push, monitor_fila
from escalaconnect.push import notificar_push
from escalaconnect.regras import RegraDeNegocio
from evento.models import Evento, Notification
from ocupado.models import Ocupado

from .models import Desistencia, Escala, EscalaFixa, EscalaFixaItem, SolicitacaoTroca
from .services import onde_serve_no_evento

logger = logging.getLogger(__name__)

# Fim de cada turno (hora local de início do culto): manhã até 12h, tarde até 17h, noite depois.
FIM_DA_MANHA, FIM_DA_TARDE = 12, 17
# Espera antes do aviso de resumo: junta num push só os cultos preenchidos em sequência.
ESPERA_DO_AVISO = getattr(settings, 'ESCALA_FIXA_ESPERA_DO_AVISO', 120)


DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
TURNOS = {EscalaFixaItem.TURNO_MANHA: 'de manhã', EscalaFixaItem.TURNO_TARDE: 'à tarde',
          EscalaFixaItem.TURNO_NOITE: 'à noite'}


def rotulo_do_culto(dia_semana, turno):
    """'Domingo de manhã', 'Quarta à noite'."""
    return f'{DIAS[dia_semana].capitalize()} {TURNOS[turno]}'


def rotulo_da_semana(dia_semana, semana):
    """'Todo domingo', 'Toda quarta', '1º domingo do mês', '3ª quarta do mês'."""
    feminino = dia_semana < 5
    if semana == EscalaFixaItem.TODA_SEMANA:
        return f"{'Toda' if feminino else 'Todo'} {DIAS[dia_semana]}"
    return f"{semana}{'ª' if feminino else 'º'} {DIAS[dia_semana]} do mês"


def turno_de(data):
    hora = timezone.localtime(data).hour
    if hora < FIM_DA_MANHA:
        return EscalaFixaItem.TURNO_MANHA
    if hora < FIM_DA_TARDE:
        return EscalaFixaItem.TURNO_TARDE
    return EscalaFixaItem.TURNO_NOITE


def ocorrencia_no_mes(data):
    """1 para o 1º domingo (ou quarta…) do mês, 2 para o 2º, até 5."""
    return (timezone.localtime(data).day - 1) // 7 + 1


def itens_do_culto(itens, evento):
    """Linhas da escala fixa que valem para este culto.

    Em cada função, as linhas daquela semana do mês ("3º domingo") valem no lugar das de
    "toda semana"; as outras funções continuam com as de "toda semana".
    """
    inicio = timezone.localtime(evento.data_inicio)
    semana = ocorrencia_no_mes(inicio)
    do_culto = [i for i in itens if i.dia_semana == inicio.weekday() and i.turno == turno_de(inicio)]
    com_semana_propria = {i.funcao_id for i in do_culto if i.semana == semana}
    return [
        i for i in do_culto
        if i.semana == semana or (i.semana == EscalaFixaItem.TODA_SEMANA and i.funcao_id not in com_semana_propria)
    ]


def eventos_da_equipe(equipe):
    """Cultos futuros em que a equipe serve: os públicos e os da própria equipe."""
    return (
        Evento.objects.filter(data_inicio__gt=timezone.now())
        .filter(Q(equipe__isnull=True) | Q(equipe=equipe))
        .order_by('data_inicio')
    )


def novo_resultado(desligada=False):
    return {'preenchidas': 0, 'puladas': [], 'liberadas': 0, 'nao_alteradas': [], 'desligada': desligada}


def _resumo(escala, pessoa, motivo):
    return {
        'evento': escala.evento.nome,
        'data': escala.evento.data_inicio,
        'funcao': escala.funcao.nome,
        'pessoa': pessoa.get_full_name() or pessoa.username,
        'motivo': motivo,
    }


def _motivo_para_pular(item, evento, membros):
    if item.usuario_id not in membros:
        return 'não é mais membro da equipe'
    onde = onde_serve_no_evento([(evento.pk, item.usuario_id)]).get((evento.pk, item.usuario_id))
    if onde:
        return f'já está escalado neste culto ({onde})'
    if Ocupado.objects.filter(usuario_id=item.usuario_id, data_inicio__lt=evento.data_fim,
                              data_fim__gt=evento.data_inicio).exists():
        return 'marcou que está ocupado nesse horário'
    return None


def _agendar_aviso(usuario_id):
    from api.tasks import avisar_escala_fixa_task

    try:
        avisar_escala_fixa_task.apply_async(args=[usuario_id], countdown=ESPERA_DO_AVISO)
    except Exception as erro:
        # Fila fora do ar: a escala já está salva; o aviso fica pendente para a próxima vez.
        logger.exception('Aviso da escala fixa não enfileirado: usuário %s', usuario_id)
        monitor_fila.falhou_ao_enfileirar('Aviso da escala fixa', erro)
    else:
        monitor_fila.enfileirou()


def aplicar_escala_fixa(equipe, eventos=None, resultado=None):
    """Preenche os cultos futuros (ou só `eventos`) com a escala fixa ativa da equipe.

    Só entra nos cultos que têm a função da linha: quem cadastra o culto decide em quais a equipe
    serve, incluindo ou não a função. Pode rodar quantas vezes quiser: cada linha preenche cada
    culto uma vez só. Usa a vaga em aberto da função; com mais pessoas na mesma função do que
    vagas, cria a vaga que falta. Quem não pode servir naquele culto fica de fora e a vaga fica em
    aberto para o líder (`puladas`).
    """
    resultado = resultado if resultado is not None else novo_resultado()
    fixa = EscalaFixa.objects.filter(equipe=equipe, ativa=True).first()
    if fixa is None:
        return resultado
    itens = list(fixa.itens.select_related('funcao', 'usuario'))
    if not itens:
        return resultado

    agora = timezone.now()
    if eventos is None:
        eventos = eventos_da_equipe(equipe)
    else:
        eventos = [e for e in eventos if e.data_inicio > agora and e.equipe_id in (None, equipe.pk)]
    membros = set(MembrosEquipe.objects.filter(equipe=equipe, aprovado=True).values_list('usuario_id', flat=True))

    avisar = set()
    with transaction.atomic():
        for evento in eventos:
            funcoes_do_culto = set(Escala.objects.filter(evento=evento).values_list('funcao_id', flat=True))
            aplicaveis = [i for i in itens_do_culto(itens, evento) if i.funcao_id in funcoes_do_culto]
            if not aplicaveis:
                continue
            feitos = set(Escala.objects.filter(evento=evento, item_fixo__in=aplicaveis)
                         .values_list('item_fixo_id', flat=True))
            for item in aplicaveis:
                if item.pk in feitos:
                    continue
                escala = (
                    Escala.objects.filter(evento=evento, funcao=item.funcao, usuario__isnull=True,
                                          item_fixo__isnull=True).order_by('pk').first()
                    or Escala(evento=evento, funcao=item.funcao)
                )
                escala.evento = evento
                escala.item_fixo = item
                motivo = _motivo_para_pular(item, evento, membros)
                if motivo:
                    escala.save()  # a vaga fica em aberto, marcada para não tentar de novo
                    resultado['puladas'].append(_resumo(escala, item.usuario, motivo))
                    continue
                escala.usuario = item.usuario
                escala.aviso_pendente = True
                escala._sem_aviso = True  # o aviso sai em resumo (avisar_escala_fixa_task)
                escala.save()
                resultado['preenchidas'] += 1
                avisar.add(item.usuario_id)
        for usuario_id in avisar:
            transaction.on_commit(lambda usuario_id=usuario_id: _agendar_aviso(usuario_id))
    return resultado


def aplicar_no_evento(evento, equipe_id=None):
    """Culto recém-cadastrado ou com vaga nova: aplica as escalas fixas ativas que valem para ele
    (só da equipe `equipe_id`, quando informada)."""
    fixas = EscalaFixa.objects.filter(ativa=True).select_related('equipe')
    if evento.equipe_id:
        fixas = fixas.filter(equipe_id=evento.equipe_id)
    if equipe_id:
        fixas = fixas.filter(equipe_id=equipe_id)
    for fixa in fixas:
        aplicar_escala_fixa(fixa.equipe, eventos=[evento])


def avisar_escalas_pendentes(usuario_id):
    """Um push só com todos os cultos que a escala fixa preencheu para a pessoa desde o último aviso."""
    with transaction.atomic():
        escalas = list(
            Escala.objects.select_for_update(skip_locked=True, of=('self',))
            .filter(usuario_id=usuario_id, aviso_pendente=True, evento__data_fim__gt=timezone.now())
            .select_related('evento', 'funcao')
        )
        Escala.objects.filter(pk__in=[e.pk for e in escalas]).update(aviso_pendente=False)
    if not escalas:
        return False
    if len(escalas) == 1:
        tipo, purpose, escala_id = 'escalado', Notification.PURPOSE_ASSIGNED, escalas[0].pk
    else:
        # 'escala_fixa' abre a lista de escalas no app.
        tipo, purpose, escala_id = 'escala_fixa', Notification.PURPOSE_FIXED_ASSIGNED, None
    notificar_push(usuario_id, *mensagens_push.escala_fixa(escalas), tipo=tipo, purpose=purpose, escala_id=escala_id)
    return True


# ── Configuração (site e app do líder) ──

def escala_fixa_da_equipe(equipe):
    fixa, _ = EscalaFixa.objects.get_or_create(equipe=equipe)
    return fixa


def definir_ativa(equipe, ativa):
    """Liga ou desliga a escala fixa. Ao ligar, já preenche os cultos cadastrados."""
    fixa = escala_fixa_da_equipe(equipe)
    fixa.ativa = bool(ativa)
    fixa.save()
    return aplicar_escala_fixa(equipe) if fixa.ativa else novo_resultado()


def _validar(fixa, dia_semana, turno, semana, funcao, usuario, item=None):
    if dia_semana not in dict(EscalaFixaItem.DIAS):
        raise RegraDeNegocio('Dia da semana inválido.', code='dia_invalido')
    if turno not in dict(EscalaFixaItem.TURNOS):
        raise RegraDeNegocio('Turno inválido.', code='turno_invalido')
    if semana not in dict(EscalaFixaItem.SEMANAS):
        raise RegraDeNegocio('Semana do mês inválida.', code='semana_invalida')
    if funcao.equipe_id != fixa.equipe_id:
        raise RegraDeNegocio('Essa função é de outra equipe.', code='funcao_de_outra_equipe')
    if not MembrosEquipe.objects.filter(equipe_id=fixa.equipe_id, usuario=usuario, aprovado=True).exists():
        raise RegraDeNegocio('Essa pessoa não é membro da equipe.', code='nao_membro')
    repetida = fixa.itens.filter(dia_semana=dia_semana, turno=turno, semana=semana, funcao=funcao, usuario=usuario)
    if item is not None:
        repetida = repetida.exclude(pk=item.pk)
    if repetida.exists():
        raise RegraDeNegocio('Essa linha já existe na escala fixa.', code='linha_repetida')


def adicionar_item(equipe, dia_semana, turno, semana, funcao, usuario):
    fixa = escala_fixa_da_equipe(equipe)
    _validar(fixa, dia_semana, turno, semana, funcao, usuario)
    item = EscalaFixaItem.objects.create(
        escala_fixa=fixa, dia_semana=dia_semana, turno=turno, semana=semana, funcao=funcao, usuario=usuario)
    return item, aplicar_escala_fixa(equipe, resultado=novo_resultado(desligada=not fixa.ativa))


def _tem_pedido(escala):
    return (Desistencia.objects.filter(escala=escala, aprovada=False).exists()
            or SolicitacaoTroca.objects.filter(escala_origem=escala, aprovada=False).exists())


def _desfazer(item, resultado, desvincular=False):
    """Tira das escalas futuras da linha quem ainda não confirmou (a escala vira vaga).

    As já confirmadas, ou com pedido à espera, ficam como estão e entram em `nao_alteradas`.
    Devolve [(escala, quem_estava)].
    """
    liberadas = []
    escalas = item.escalas.filter(evento__data_inicio__gt=timezone.now()).select_related('evento', 'funcao', 'usuario')
    for escala in escalas:
        if escala.usuario_id and escala.usuario_id != item.usuario_id:
            continue  # o líder colocou outra pessoa nesse culto: a troca dele vale
        if escala.usuario_id and (escala.confirmada or _tem_pedido(escala)):
            resultado['nao_alteradas'].append(_resumo(escala, escala.usuario, 'já confirmada' if escala.confirmada
                                                      else 'tem um pedido à espera'))
            if desvincular:
                escala.item_fixo = None
                escala.save(update_fields=['item_fixo'])
            continue
        anterior = escala.usuario_id
        escala.usuario = None
        escala.item_fixo = None
        escala.aviso_pendente = False
        escala._sem_aviso = True
        escala.save()
        liberadas.append((escala, anterior))
    return liberadas


def _avisar_quem_saiu(liberadas, resultado):
    """Depois de reaplicar: quem estava e não serve mais naquele culto recebe um aviso."""
    saiu = defaultdict(list)
    for escala, anterior in liberadas:
        escala.refresh_from_db(fields=['usuario', 'aviso_pendente'])
        if anterior is None:
            continue
        if escala.usuario_id is None:
            resultado['liberadas'] += 1
        if escala.usuario_id == anterior:
            # Continua na mesma escala: não precisa de aviso de novo.
            Escala.objects.filter(pk=escala.pk).update(aviso_pendente=False)
            continue
        if not Escala.objects.filter(evento=escala.evento, usuario_id=anterior).exists():
            saiu[anterior].append(escala)
    for usuario_id, escalas in saiu.items():
        notificar_push(usuario_id, *mensagens_push.saiu_da_escala_fixa(escalas),
                       tipo='saiu_da_escala', purpose=Notification.PURPOSE_FIXED_CHANGED,
                       escala_id=escalas[0].pk if len(escalas) == 1 else None)


def atualizar_item(item, dia_semana, turno, semana, funcao, usuario):
    """Muda a linha e refaz os cultos futuros que ela tinha preenchido (só os não confirmados)."""
    fixa = item.escala_fixa
    _validar(fixa, dia_semana, turno, semana, funcao, usuario, item=item)
    resultado = novo_resultado(desligada=not fixa.ativa)
    with transaction.atomic():
        liberadas = _desfazer(item, resultado)
        item.dia_semana, item.turno, item.semana, item.funcao, item.usuario = dia_semana, turno, semana, funcao, usuario
        item.save()
        aplicar_escala_fixa(fixa.equipe, resultado=resultado)
        _avisar_quem_saiu(liberadas, resultado)
    return resultado


def excluir_item(item):
    """Apaga a linha: os cultos futuros que ela preenchia (não confirmados) viram vaga."""
    fixa = item.escala_fixa
    resultado = novo_resultado(desligada=not fixa.ativa)
    with transaction.atomic():
        liberadas = _desfazer(item, resultado, desvincular=True)
        item.delete()
        aplicar_escala_fixa(fixa.equipe, resultado=resultado)
        _avisar_quem_saiu(liberadas, resultado)
    return resultado


def descrever_resultado(resultado):
    """Frase curta para o líder depois de salvar (site e app)."""
    partes = []
    n = resultado['preenchidas']
    if n:
        partes.append('1 culto preenchido' if n == 1 else f'{n} cultos preenchidos')
    if resultado['liberadas']:
        n = resultado['liberadas']
        partes.append('1 vaga ficou em aberto' if n == 1 else f'{n} vagas ficaram em aberto')
    if resultado['puladas']:
        n = len(resultado['puladas'])
        partes.append('1 pessoa não pôde ser escalada' if n == 1 else f'{n} escalas não puderam ser feitas')
    if resultado['nao_alteradas']:
        n = len(resultado['nao_alteradas'])
        partes.append('1 escala já confirmada não mudou' if n == 1 else f'{n} escalas já confirmadas não mudaram')
    if not partes and resultado.get('desligada'):
        return 'Linha salva. Ligue a escala fixa para preencher os cultos.'
    return ' · '.join(partes) or 'Nenhum culto cadastrado precisou de mudança.'
