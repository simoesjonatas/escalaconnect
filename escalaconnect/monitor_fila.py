"""Monitor da fila do Celery: avisa quando o worker ou o beat param.

Em novembro de 2026 o worker e o beat ficaram 10 dias parados sem ninguém perceber: o site seguia
respondendo e quem enfileira engole o erro de propósito (escalaconnect/push.py), para a ação do
usuário não virar erro 500. Aqui ficam:

- o batimento: a tarefa `escalaconnect.batimento` (escalaconnect/celery.py), que o beat agenda a cada
  5 min; o worker, ao rodá-la, grava a hora no cache. Batimento velho = worker ou beat parado;
- `verificar()`: o que está errado agora (a fila recusa tarefas, worker ou beat sem batimento);
- `avisar()`: e-mail aos ADMINS, no máximo um por problema a cada MONITOR_FILA_AVISO_HORAS;
- os ganchos de quem enfileira: `falhou_ao_enfileirar()` no except e `enfileirou()` depois do
  sucesso (de tempos em tempos confere se alguém está consumindo a fila).

O batimento só faz sentido com o cache compartilhado entre web e worker (CACHE_URL, Redis): sem ele
cada processo tem o seu cache e o web nunca veria o batimento (MONITOR_FILA_BATIMENTO desliga).
Tudo aqui roda dentro de requests e callbacks de commit: nunca pode levantar exceção.
"""
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.core.mail import get_connection, mail_admins

logger = logging.getLogger(__name__)

CHAVE_WORKER = 'fila:batimento:worker'  # última vez que o worker rodou o batimento (qualquer origem)
CHAVE_BEAT = 'fila:batimento:beat'  # última vez que rodou um batimento agendado pelo beat
CHAVE_DESDE = 'fila:monitor:desde'  # desde quando o monitor olha (carência quando nunca houve batimento)
CHAVE_PING = 'fila:monitor:ping'  # trava: o /healthz/celery publica no máx. um teste a cada PING_SEGUNDOS
CHAVE_PING_ERRO = 'fila:monitor:ping:erro'  # resultado do último teste de publicação ('' = aceitou)
CHAVE_VIGIA = 'fila:monitor:vigia'  # trava: a conferência depois de enfileirar roda no máx. 1x a cada VIGIA_SEGUNDOS
PREFIXO_AVISO = 'fila:monitor:aviso:'  # trava de cada e-mail, por código de problema

PING_SEGUNDOS = 30
VIGIA_SEGUNDOS = 5 * 60

TITULOS = {
    'fila_indisponivel': 'a fila do Celery não aceita tarefas',
    'worker_parado': 'o worker do Celery não está rodando tarefas',
    'beat_parado': 'o beat do Celery não está agendando tarefas',
}

# Trava local (por processo), usada quando o cache não responde: sem ela, Redis fora do ar
# viraria um e-mail por push.
_travas_locais = {}


class Problema:
    def __init__(self, codigo, detalhe):
        self.codigo = codigo
        self.detalhe = detalhe

    @property
    def titulo(self):
        return TITULOS.get(self.codigo, self.codigo)

    def como_dict(self):
        return {'codigo': self.codigo, 'detalhe': self.detalhe}

    def __repr__(self):
        return f'Problema({self.codigo!r}, {self.detalhe!r})'


def _trava_local(chave, segundos):
    agora = time.monotonic()
    ultima = _travas_locais.get(chave)
    if ultima is not None and agora - ultima < segundos:
        return False
    _travas_locais[chave] = agora
    return True


def _pode(chave, segundos):
    """True uma vez a cada `segundos` entre todos os processos (cache.add como trava).

    Sem cache (Redis fora do ar, por exemplo), a trava passa a ser por processo.
    """
    try:
        return bool(cache.add(chave, 1, segundos))
    except Exception:
        logger.warning('Monitor da fila: cache indisponível, usando a trava local (%s)', chave)
        return _trava_local(chave, segundos)


def _ler(chave):
    try:
        return cache.get(chave)
    except Exception:
        logger.warning('Monitor da fila: cache indisponível ao ler %s', chave)
        return None


def _gravar(chave, valor, segundos=None):
    try:
        cache.set(chave, valor, segundos)
    except Exception:
        logger.warning('Monitor da fila: cache indisponível ao gravar %s', chave)


def registrar_batimento(origem):
    """Roda no worker (tarefa escalaconnect.batimento): grava a hora do batimento."""
    agora = time.time()
    cache.set(CHAVE_WORKER, agora, None)
    if origem == 'beat':
        cache.set(CHAVE_BEAT, agora, None)


def _minutos(segundos):
    minutos = int(segundos // 60)
    if minutos < 120:
        return f'{minutos} min'
    horas = minutos // 60
    return f'{horas} h' if horas < 48 else f'{horas // 24} dias'


def _publicar_teste():
    """Publica um batimento de teste: confirma que a fila aceita tarefas (e alimenta o batimento do worker).

    Devolve o erro (texto) ou '' quando a fila aceitou. Com a trava fechada (outro teste há menos de
    PING_SEGUNDOS), repete o resultado do último teste; None se não houver.
    """
    if not _pode(CHAVE_PING, PING_SEGUNDOS):
        return _ler(CHAVE_PING_ERRO)
    from escalaconnect.celery import batimento

    try:
        # expires: se o worker estiver parado, os testes não se acumulam na fila.
        batimento.apply_async(kwargs={'origem': 'monitor'}, expires=PING_SEGUNDOS * 4)
        erro = ''
    except Exception as exc:
        erro = f'{type(exc).__name__}: {exc}'
    _gravar(CHAVE_PING_ERRO, erro, PING_SEGUNDOS * 4)
    return erro


def estado(publicar=False):
    """Retrato da fila agora: {'problemas': [Problema], 'worker_seg': ..., 'beat_seg': ..., ...}.

    `publicar=True` também publica um batimento de teste (o /healthz/celery faz isso).
    `worker_seg`/`beat_seg`: segundos desde o último batimento (None = nunca visto).
    """
    problemas = []
    resultado = {'problemas': problemas, 'batimento': bool(settings.MONITOR_FILA_BATIMENTO)}

    if publicar:
        erro = _publicar_teste()
        resultado['fila_aceita'] = None if erro is None else not erro
        if erro:
            problemas.append(Problema('fila_indisponivel', f'A tarefa de teste não entrou na fila ({erro}).'))

    if not settings.MONITOR_FILA_BATIMENTO:
        return resultado

    agora = time.time()
    limite = settings.MONITOR_FILA_MINUTOS * 60
    try:
        cache.add(CHAVE_DESDE, agora, None)
    except Exception:
        pass
    desde = _ler(CHAVE_DESDE) or agora
    worker, beat = _ler(CHAVE_WORKER), _ler(CHAVE_BEAT)
    resultado['worker_seg'] = None if worker is None else int(agora - worker)
    resultado['beat_seg'] = None if beat is None else int(agora - beat)

    def parado(ultimo):
        # Nunca visto: só é problema depois da carência (deploy novo, Redis zerado).
        return agora - (ultimo if ultimo is not None else desde) > limite

    if parado(worker):
        visto = f'há {_minutos(agora - worker)}' if worker is not None else 'nenhuma vez desde que o monitor começou'
        problemas.append(Problema(
            'worker_parado',
            f'Nenhum batimento rodou {visto} (o beat agenda um a cada 5 min; limite: '
            f'{settings.MONITOR_FILA_MINUTOS} min): o worker está parado ou o beat parou de agendar.'))
    elif parado(beat):
        # O worker roda tarefas (testes do /healthz/celery), mas nenhuma vinda do beat.
        visto = f'há {_minutos(agora - beat)}' if beat is not None else 'nenhuma vez desde que o monitor começou'
        problemas.append(Problema(
            'beat_parado',
            f'O worker está de pé, mas o batimento agendado pelo beat não roda {visto}: os lembretes '
            f'e a escala fixa também não estão saindo.'))
    return resultado


def verificar(publicar=False):
    """Os problemas da fila agora (lista vazia = tudo certo)."""
    return estado(publicar=publicar)['problemas']


def avisar(problemas):
    """Manda um e-mail aos ADMINS por problema, no máximo um a cada MONITOR_FILA_AVISO_HORAS.

    Devolve quantos e-mails saíram.
    """
    enviados = 0
    for problema in problemas:
        try:
            if not _pode(PREFIXO_AVISO + problema.codigo, settings.MONITOR_FILA_AVISO_HORAS * 3600):
                continue
            logger.error('Monitor da fila: %s. %s', problema.titulo, problema.detalhe)
            if not settings.ADMINS:
                logger.error('Monitor da fila: ADMINS vazio no .env; o aviso por e-mail não saiu.')
                continue
            corpo = (
                f'{problema.detalhe}\n\n'
                'Enquanto isso, push, lembretes e e-mails de confirmação não saem.\n\n'
                'O que olhar na VPS, na pasta do projeto:\n'
                '  docker compose ps\n'
                '  docker compose logs --tail 100 celeryworker celerybeat\n\n'
                'Situação agora: /healthz/celery no site.\n'
                f'Este aviso não se repete por {settings.MONITOR_FILA_AVISO_HORAS} h '
                '(veja docs/monitoramento-celery.md).'
            )
            # Timeout curto: isto roda dentro de um request; SMTP travado não pode segurar a resposta.
            conexao = get_connection(fail_silently=True, timeout=10)
            mail_admins(f'Celery: {problema.titulo}', corpo, fail_silently=True, connection=conexao)
            enviados += 1
        except Exception:
            logger.exception('Monitor da fila: falha ao avisar (%s)', problema.codigo)
    return enviados


def falhou_ao_enfileirar(onde, erro):
    """Gancho do except de quem enfileira: a fila recusou a tarefa. Avisa os admins (com limite)."""
    try:
        avisar([Problema('fila_indisponivel', f'{onde}: a tarefa não entrou na fila ({type(erro).__name__}: {erro}).')])
    except Exception:
        logger.exception('Monitor da fila: falha no aviso de fila indisponível')


def enfileirou():
    """Gancho depois de enfileirar com sucesso: de tempos em tempos confere se o worker e o beat batem.

    A fila pode aceitar a tarefa sem ninguém do outro lado (worker parado com o Redis de pé).
    Custo quase zero: trava local de VIGIA_SEGUNDOS por processo antes de tocar no cache.
    """
    try:
        if not settings.MONITOR_FILA_BATIMENTO:
            return
        if not _trava_local(CHAVE_VIGIA, VIGIA_SEGUNDOS) or not _pode(CHAVE_VIGIA, VIGIA_SEGUNDOS):
            return
        avisar(verificar())
    except Exception:
        logger.exception('Monitor da fila: falha ao conferir o batimento')


# === Retrato para a página de monitoramento (usuario/views_monitor.py, só superusuário) ===

# O que cada tarefa agendada faz, para a lista do beat. Sem entrada aqui, vale a docstring.
DESCRICOES = {
    'api.tasks.lembretes_de_escala': 'Lembretes de escala pelo app (véspera, dia e última chamada)',
    'api.tasks.limpar_avisos_antigos': 'Apaga da caixa do app os avisos com mais de 60 dias',
    'api.tasks.aplicar_escalas_fixas': 'Preenche pela escala fixa os cultos que ficaram sem',
    'escalaconnect.batimento': 'Batimento do monitor da fila (prova que o beat e o worker estão de pé)',
}
LIMITE_ARGS = 160  # caracteres dos argumentos mostrados por tarefa


def _encurtar(texto):
    texto = str(texto or '')
    return texto if len(texto) <= LIMITE_ARGS else texto[:LIMITE_ARGS - 1] + '…'


def _data(valor):
    """ISO (como o Celery manda eta/expires) para datetime local; None se não der."""
    from datetime import datetime

    from django.utils import timezone

    if not valor:
        return None
    try:
        data = datetime.fromisoformat(str(valor))
    except ValueError:
        return None
    return timezone.localtime(data) if timezone.is_aware(data) else data


def _resumo_da_mensagem(bruta):
    """Mensagem crua da fila no Redis (JSON do kombu, protocolo 2 do Celery) para exibir."""
    import json

    try:
        cabecalhos = json.loads(bruta).get('headers') or {}
    except (TypeError, ValueError):
        return {'tarefa': '(mensagem ilegível)', 'id': '', 'args': '', 'eta': None, 'expira': None}
    args = ' '.join(filter(None, [cabecalhos.get('argsrepr'), cabecalhos.get('kwargsrepr')]))
    return {
        'tarefa': cabecalhos.get('task', '?'),
        'id': cabecalhos.get('id', ''),
        'args': _encurtar(args),
        'eta': _data(cabecalhos.get('eta')),
        'expira': _data(cabecalhos.get('expires')),
    }


def fila_no_broker(limite=20):
    """O que espera na fila padrão do broker, ainda não entregue ao worker.

    Com o worker de pé fica quase sempre vazia: ele pega as mensagens na hora, inclusive as com
    countdown (essas ficam com ele, em tarefas_no_worker). Fila crescendo = worker parado ou lento.
    {'fila': nome, 'total': int|None, 'proximas': [...], 'erro': str|None}; `proximas` só no Redis.
    """
    from escalaconnect.celery import app

    nome = app.conf.task_default_queue
    try:
        # Timeout curto: a página não pode ficar presa com o Redis fora.
        with app.connection_for_read(connect_timeout=2) as conexao:
            canal = conexao.default_channel
            total = canal.queue_declare(queue=nome).message_count
            proximas = []
            cliente = getattr(canal, 'client', None)
            if total and hasattr(cliente, 'lrange'):
                # O kombu publica com LPUSH e o worker consome com BRPOP: a próxima fica no fim.
                proximas = [_resumo_da_mensagem(m) for m in reversed(cliente.lrange(nome, -limite, -1))]
            return {'fila': nome, 'total': total, 'proximas': proximas, 'erro': None}
    except Exception as exc:
        return {'fila': nome, 'total': None, 'proximas': [], 'erro': f'{type(exc).__name__}: {exc}'}


def _resumo_do_pedido(pedido, eta=None):
    args = pedido.get('args')
    kwargs = pedido.get('kwargs')
    texto = ' '.join(str(parte) for parte in (args, kwargs) if parte not in (None, '', [], (), {}))
    return {
        'tarefa': pedido.get('name') or pedido.get('type') or '?',
        'id': pedido.get('id', ''),
        'args': _encurtar(texto),
        'eta': _data(eta),
        'inicio': pedido.get('time_start'),
    }


def tarefas_no_worker(espera=1.0):
    """O que o worker tem em mãos: rodando, reservadas e agendadas (countdown/eta).

    None quando nenhum worker responde em `espera` segundos. Pergunta a um worker só (limit=1):
    em produção há um container de worker.
    """
    from escalaconnect.celery import app

    try:
        inspecao = app.control.inspect(timeout=espera, limit=1)
        rodando = inspecao.active()
        if not rodando:
            return None
        reservadas = inspecao.reserved() or {}
        agendadas = inspecao.scheduled() or {}
    except Exception:
        logger.warning('Monitor da fila: o worker não respondeu ao inspect', exc_info=True)
        return None
    worker = next(iter(rodando))
    return {
        'worker': worker,
        'rodando': [_resumo_do_pedido(p) for p in rodando.get(worker, [])],
        'reservadas': [_resumo_do_pedido(p) for p in reservadas.get(worker, [])],
        'agendadas': sorted(
            (_resumo_do_pedido(a.get('request') or {}, a.get('eta')) for a in agendadas.get(worker, [])),
            key=lambda t: (t['eta'] is None, t['eta'] or 0)),
    }


def _descrever_horario(horario):
    from datetime import timedelta

    from celery.schedules import crontab

    if isinstance(horario, (int, float)):
        horario = timedelta(seconds=horario)
    if isinstance(horario, timedelta):
        return f'a cada {_minutos(horario.total_seconds())}'
    run_every = getattr(horario, 'run_every', None)
    if not isinstance(horario, crontab):
        return f'a cada {_minutos(run_every.total_seconds())}' if isinstance(run_every, timedelta) else str(horario)
    minuto, hora = str(horario._orig_minute), str(horario._orig_hour)
    resto = (horario._orig_day_of_week, horario._orig_day_of_month, horario._orig_month_of_year)
    if all(str(campo) == '*' for campo in resto):
        if hora == '*' and minuto.startswith('*/'):
            return f'a cada {minuto[2:]} min'
        if hora == '*' and minuto == '*':
            return 'a cada minuto'
        if minuto.isdigit() and hora.isdigit():
            return f'todo dia às {int(hora):02d}:{int(minuto):02d}'
    return 'cron ' + ' '.join(str(c) for c in (minuto, hora) + resto)


def agenda_do_beat():
    """As tarefas do CELERY_BEAT_SCHEDULE com a próxima execução, da mais próxima para a mais distante.

    A próxima vem do horário (o crontab independe da última execução). Só vale com o beat de pé.
    """
    from datetime import timedelta

    from escalaconnect.celery import app

    # Hora local do Celery: o crontab lê hora/minuto do datetime que recebe (é o que o beat usa).
    agora = app.now()
    itens = []
    for nome, entrada in app.conf.beat_schedule.items():
        horario = entrada['schedule']
        proxima = None
        try:
            if hasattr(horario, 'remaining_estimate'):
                # Arredonda ao minuto: o Celery devolve 12:09:59.998 para 12:10.
                proxima = (agora + horario.remaining_estimate(agora) + timedelta(seconds=30)).replace(
                    second=0, microsecond=0)
        except Exception:
            logger.warning('Monitor da fila: não calculei a próxima de %s', nome, exc_info=True)
        tarefa = entrada['task']
        descricao = DESCRICOES.get(tarefa)
        if not descricao:
            registrada = app.tasks.get(tarefa)
            descricao = ((registrada.__doc__ or '').strip().splitlines() or [''])[0] if registrada else ''
        itens.append({
            'nome': nome, 'tarefa': tarefa, 'descricao': descricao,
            'quando': _descrever_horario(horario), 'proxima': proxima,
        })
    return sorted(itens, key=lambda item: (item['proxima'] is None, item['proxima'] or 0))
