"""Regras das escalas do voluntário, compartilhadas entre o site e a API do app."""
from datetime import timedelta

from django.db.models import Exists, OuterRef
from django.utils import timezone

from equipe.models import MembrosEquipe
from escalaconnect import mensagens_push
from escalaconnect.push import notificar_push
from escalaconnect.regras import RegraDeNegocio
from evento.models import Notification

from .models import Desistencia, Escala, Rendimento, SolicitacaoTroca

DIAS_DE_VAGAS = 60


def escalas_futuras(usuario):
    """Escalas do usuário em eventos que começam de hoje em diante."""
    return Escala.objects.filter(
        usuario=usuario,
        # "Hoje" no fuso local: com a data em UTC, depois das 21h os eventos
        # do próprio dia sumiam da lista.
        evento__data_inicio__date__gte=timezone.localdate(),
    )


def _avisar_saida_da_escala(usuario_id, escala, mensagem, purpose):
    notificar_push(
        usuario_id, *mensagem(escala),
        tipo='saiu_da_escala', purpose=purpose, escala_id=escala.pk,
    )


def _avisar_pedido_recusado(usuario_id, escala):
    # A pessoa continua escalada: o toque abre a escala, como no aviso de escalado.
    notificar_push(
        usuario_id, *mensagens_push.pedido_recusado(escala),
        tipo='pedido_recusado', purpose=Notification.PURPOSE_REQUEST_DECLINED, escala_id=escala.pk,
    )


def _exigir_dono(escala, usuario, mensagem):
    if escala.usuario_id != usuario.pk:
        raise RegraDeNegocio(mensagem, code='escala_de_outro_usuario')


# ── Confirmação ──

def validar_confirmacao(escala, usuario):
    _exigir_dono(escala, usuario, "Você só pode confirmar sua própria escala.")
    if escala.evento.data_fim < timezone.now():
        raise RegraDeNegocio(
            "Você não pode confirmar uma escala de um evento já encerrado.", code='evento_encerrado')
    if escala.confirmada:
        raise RegraDeNegocio("Esta escala já foi confirmada anteriormente.", code='ja_confirmada')


def confirmar_escala(escala, usuario):
    validar_confirmacao(escala, usuario)
    escala.confirmada = True
    escala.data_confirmacao = timezone.now()
    escala.save()
    return escala


# ── Impedimento (desistência com motivo) ──

def validar_impedimento(escala, usuario):
    _exigir_dono(escala, usuario, "Você só pode sinalizar impedimento na sua própria escala.")
    if escala.evento.data_inicio <= timezone.now():
        raise RegraDeNegocio(
            "Não é possível sinalizar desistência após o início do evento.", code='evento_iniciado')
    if Desistencia.objects.filter(escala=escala, usuario=usuario, aprovada=False).exists():
        raise RegraDeNegocio("Você já sinalizou desistência para esta escala.", code='ja_sinalizado')
    # Um pedido por vez: o líder não precisa avaliar impedimento e troca da mesma escala.
    if SolicitacaoTroca.objects.filter(escala_origem=escala, aprovada=False).exists():
        raise RegraDeNegocio(
            "Você já pediu troca desta escala. Cancele o pedido de troca para sinalizar impedimento.",
            code='troca_pendente')


def sinalizar_impedimento(escala, usuario, motivo):
    validar_impedimento(escala, usuario)
    return Desistencia.objects.create(escala=escala, usuario=usuario, motivo=motivo)


def cancelar_impedimento(escala, usuario):
    """O voluntário desiste do impedimento ainda em análise e continua escalado."""
    _exigir_dono(escala, usuario, "Você só pode cancelar o impedimento da sua própria escala.")
    apagados, _ = Desistencia.objects.filter(escala=escala, aprovada=False).delete()
    if not apagados:
        raise RegraDeNegocio("Nenhum impedimento em análise encontrado.", code='sem_impedimento')


def aprovar_desistencia(desistencia):
    """Aprova a desistência e libera a vaga. Devolve False se já estava aprovada."""
    if desistencia.aprovada:
        return False
    desistencia.aprovada = True
    desistencia.data_aprovacao = timezone.now()
    desistencia.save()
    desistencia.escala.clear_escala()
    _avisar_saida_da_escala(
        desistencia.usuario_id, desistencia.escala, mensagens_push.impedimento_aceito,
        Notification.PURPOSE_WITHDRAWAL_APPROVED)
    return True


def recusar_desistencia(desistencia):
    """Descarta o impedimento: a pessoa continua escalada e é avisada."""
    if desistencia.aprovada:
        raise RegraDeNegocio("Este impedimento já foi aprovado.", code='ja_aprovado')
    escala = desistencia.escala
    desistencia.delete()
    _avisar_pedido_recusado(desistencia.usuario_id, escala)


# ── Solicitação de troca ──

def validar_solicitacao_troca(escala, usuario):
    _exigir_dono(escala, usuario, "Você só pode pedir troca da sua própria escala.")
    if SolicitacaoTroca.objects.filter(solicitante=usuario, escala_origem=escala, aprovada=False).exists():
        raise RegraDeNegocio(
            'Você já possui uma solicitação pendente para esta escala.', code='solicitacao_pendente')
    if Desistencia.objects.filter(escala=escala, aprovada=False).exists():
        raise RegraDeNegocio(
            "Você já sinalizou impedimento nesta escala. Cancele o impedimento para pedir troca.",
            code='impedimento_pendente')


def solicitar_troca(escala, usuario):
    validar_solicitacao_troca(escala, usuario)
    return SolicitacaoTroca.objects.create(
        escala_origem=escala,
        solicitante=usuario,
        tipo_solicitacao='desistencia',
        data_solicitacao=timezone.now(),
    )


def cancelar_troca(escala, usuario):
    _exigir_dono(escala, usuario, "Você só pode cancelar a solicitação da sua própria escala.")
    solicitacao = SolicitacaoTroca.objects.filter(escala_origem=escala, aprovada=False).first()
    if solicitacao is None:
        raise RegraDeNegocio("Nenhuma solicitação pendente encontrada.", code='sem_solicitacao')
    solicitacao.delete()


def aprovar_troca(troca, lider):
    """Aprova a troca e libera a vaga. Devolve False se já estava aprovada."""
    if troca.aprovada:
        # Não limpa a escala de novo: a vaga pode já ter sido repassada a outro voluntário.
        return False
    troca.lider_aprovador = lider
    troca.aprovada = True
    troca.data_aprovacao = timezone.now()
    troca.save()
    troca.escala_origem.clear_escala()
    _avisar_saida_da_escala(
        troca.solicitante_id, troca.escala_origem, mensagens_push.troca_aprovada, Notification.PURPOSE_SWAP_APPROVED)
    return True


def recusar_troca(troca):
    """Descarta o pedido de troca: a pessoa continua escalada e é avisada."""
    if troca.aprovada:
        raise RegraDeNegocio("Esta troca já foi aprovada.", code='ja_aprovada')
    escala = troca.escala_origem
    troca.delete()
    _avisar_pedido_recusado(troca.solicitante_id, escala)


# ── Vagas (líder) ──

def escalar_em_vaga(escala, usuario):
    """Coloca um membro aprovado da equipe numa vaga em aberto de evento futuro.

    O aviso "Você foi escalado" e o encerramento das ofertas saem pelos signals de Escala (api/signals.py).
    """
    if escala.evento.data_inicio <= timezone.now():
        raise RegraDeNegocio("O evento já começou.", code='evento_iniciado')
    if escala.usuario_id:
        raise RegraDeNegocio("Esta vaga já foi preenchida.", code='vaga_ocupada')
    if not MembrosEquipe.objects.filter(usuario=usuario, equipe=escala.equipe, aprovado=True).exists():
        raise RegraDeNegocio("Essa pessoa não é membro da equipe.", code='nao_membro')
    if Escala.objects.filter(evento=escala.evento, usuario=usuario).exists():
        raise RegraDeNegocio("Essa pessoa já está escalada neste evento.", code='ja_escalado')
    escala.usuario = usuario
    escala.save()
    return escala


def substituir_na_escala(escala, usuario):
    """Troca quem ainda não confirmou por outro membro; quem sai recebe um aviso.

    Impedimento ou troca à espera passam pela aprovação do pedido, não por aqui.
    """
    if escala.confirmada:
        raise RegraDeNegocio("Essa pessoa já confirmou a escala.", code='ja_confirmada')
    if (Desistencia.objects.filter(escala=escala, aprovada=False).exists()
            or SolicitacaoTroca.objects.filter(escala_origem=escala, aprovada=False).exists()):
        raise RegraDeNegocio("Esta escala tem um pedido à espera; decida o pedido.", code='pedido_pendente')
    anterior_id = escala.usuario_id
    escala.usuario = None
    escalar_em_vaga(escala, usuario)
    if anterior_id:
        _avisar_saida_da_escala(anterior_id, escala, mensagens_push.substituido, Notification.PURPOSE_REPLACED)
    return escala


# ── Oferta para vaga (voluntário se oferece, líder aprova) ──

def vagas_abertas_para(usuario):
    """Vagas em aberto, nos próximos 60 dias, das equipes em que o usuário é membro aprovado.

    Ficam de fora os eventos em que ele já está escalado (em qualquer função).
    """
    agora = timezone.now()
    equipes = MembrosEquipe.objects.filter(usuario=usuario, aprovado=True).values('equipe_id')
    ja_escalado = Escala.objects.filter(usuario=usuario).values('evento_id')
    return (
        Escala.objects
        .filter(usuario__isnull=True, funcao__equipe__in=equipes,
                evento__data_inicio__gt=agora, evento__data_inicio__lte=agora + timedelta(days=DIAS_DE_VAGAS))
        .exclude(evento_id__in=ja_escalado)
    )


def vagas_visiveis_para(usuario):
    """Vagas que o voluntário vê (app e site), mesmo que alguém da equipe já esteja disponível:
    só some quando alguém é escalado. Cada vaga traz `me_ofereci`.
    """
    return list(
        vagas_abertas_para(usuario)
        .select_related('evento', 'funcao__equipe')
        .annotate(me_ofereci=Exists(
            Rendimento.objects.filter(escala=OuterRef('pk'), candidato=usuario, aprovada=False)))
        .order_by('evento__data_inicio', 'funcao__equipe__nome', 'funcao__nome')
    )


def ofertas_do_voluntario(usuario):
    """Vagas em que o voluntário se ofereceu e a liderança ainda não decidiu (aba Disponibilidade)."""
    return [v for v in vagas_visiveis_para(usuario) if v.me_ofereci]


def ofertas_pendentes():
    """Ofertas que ainda valem: não aprovadas, de vaga ainda aberta em evento futuro."""
    return Rendimento.objects.filter(
        aprovada=False, escala__usuario__isnull=True, escala__evento__data_inicio__gt=timezone.now())


def oferecer_para_vaga(escala, usuario):
    if not vagas_abertas_para(usuario).filter(pk=escala.pk).exists():
        raise RegraDeNegocio("Esta vaga não está mais disponível para você.", code='vaga_indisponivel')
    oferta, _ = Rendimento.objects.get_or_create(escala=escala, candidato=usuario, aprovada=False)
    return oferta


def cancelar_oferta(escala, usuario):
    apagadas, _ = Rendimento.objects.filter(escala=escala, candidato=usuario, aprovada=False).delete()
    if not apagadas:
        raise RegraDeNegocio("Você não se ofereceu para esta vaga.", code='sem_oferta')


def aprovar_oferta(oferta):
    """Escala quem se ofereceu (push "Você foi escalado" pelo signal)."""
    return escalar_em_vaga(oferta.escala, oferta.candidato)


# Oferta recusada ou vaga que ficou com outra pessoa: sem push nem aviso (era notificação
# demais); a oferta só some da aba Disponibilidade de quem se ofereceu.

def recusar_oferta(oferta):
    oferta.delete()


def encerrar_ofertas(escala, escolhido_id):
    """Vaga preenchida: marca a oferta de quem ficou com ela e descarta as dos demais.

    Chamada pelo signal de Escala, então vale para app, site, auto-escalar e admin.
    """
    Rendimento.objects.filter(escala=escala, candidato_id=escolhido_id, aprovada=False).update(
        aprovada=True, data_aprovacao=timezone.now())
    Rendimento.objects.filter(escala=escala, aprovada=False).exclude(candidato_id=escolhido_id).delete()
