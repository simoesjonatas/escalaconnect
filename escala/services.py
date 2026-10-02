"""Regras das escalas do voluntário, compartilhadas entre o site e a API do app."""
from django.utils import timezone

from escalaconnect.regras import RegraDeNegocio

from .models import Desistencia, Escala, SolicitacaoTroca


def escalas_futuras(usuario):
    """Escalas do usuário em eventos que começam de hoje em diante."""
    return Escala.objects.filter(
        usuario=usuario,
        # "Hoje" no fuso local: com a data em UTC, depois das 21h os eventos
        # do próprio dia sumiam da lista.
        evento__data_inicio__date__gte=timezone.localdate(),
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


def sinalizar_impedimento(escala, usuario, motivo):
    validar_impedimento(escala, usuario)
    return Desistencia.objects.create(escala=escala, usuario=usuario, motivo=motivo)


def aprovar_desistencia(desistencia):
    """Aprova a desistência e libera a vaga. Devolve False se já estava aprovada."""
    if desistencia.aprovada:
        return False
    desistencia.aprovada = True
    desistencia.data_aprovacao = timezone.now()
    desistencia.save()
    desistencia.escala.clear_escala()
    return True


# ── Solicitação de troca ──

def validar_solicitacao_troca(escala, usuario):
    _exigir_dono(escala, usuario, "Você só pode pedir troca da sua própria escala.")
    if SolicitacaoTroca.objects.filter(solicitante=usuario, escala_origem=escala, aprovada=False).exists():
        raise RegraDeNegocio(
            'Você já possui uma solicitação pendente para esta escala.', code='solicitacao_pendente')


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
    return True
