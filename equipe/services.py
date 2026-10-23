from django.utils import timezone

from escala.models import Desistencia, SolicitacaoTroca
from escalaconnect import mensagens_push
from escalaconnect.push import notificar_push
from escalaconnect.regras import RegraDeNegocio
from evento.models import Notification

from .models import Equipe, MembrosEquipe


def equipes_lideradas(usuario):
    """Equipes que o usuário pode gerenciar (todas, se for staff/superuser)."""
    if usuario.is_superuser or usuario.is_staff:
        return Equipe.objects.all()
    return Equipe.objects.filter(lideranca__usuario=usuario).distinct()


def pendencias_do_lider(usuario):
    """Impedimentos, trocas e candidaturas esperando o líder (mesmo critério do painel do site)."""
    equipes = equipes_lideradas(usuario)
    agora = timezone.now()
    return {
        'impedimentos': (
            Desistencia.objects
            .filter(escala__funcao__equipe__in=equipes, aprovada=False, escala__evento__data_inicio__gte=agora)
            .select_related('escala__evento', 'escala__funcao__equipe', 'usuario')
            .order_by('escala__evento__data_inicio')
        ),
        'trocas': (
            SolicitacaoTroca.objects
            .filter(escala_origem__funcao__equipe__in=equipes, aprovada=False,
                    escala_origem__evento__data_inicio__gte=agora)
            .select_related('escala_origem__evento', 'escala_origem__funcao__equipe', 'solicitante')
            .order_by('escala_origem__evento__data_inicio')
        ),
        'candidaturas': (
            MembrosEquipe.objects
            .filter(equipe__in=equipes, aprovado=False)
            .select_related('usuario', 'equipe')
            .order_by('equipe__nome', 'usuario__first_name')
        ),
    }


def total_pendencias_do_lider(usuario):
    return sum(qs.count() for qs in pendencias_do_lider(usuario).values())


def equipes_do_usuario(usuario):
    """Devolve (aprovadas, pendentes): equipes em que o usuário participa ou aguarda aprovação."""
    membros = (
        MembrosEquipe.objects
        .filter(usuario=usuario)
        .select_related('equipe')
        .order_by('equipe__nome')
    )
    aprovadas = [m.equipe for m in membros if m.aprovado]
    pendentes = [m.equipe for m in membros if not m.aprovado]
    return aprovadas, pendentes


def equipes_disponiveis(usuario):
    """Equipes às quais o usuário ainda pode se candidatar."""
    return Equipe.objects.exclude(membros__usuario=usuario).order_by('nome')


def candidatar(usuario, equipe):
    """Registra a candidatura (pendente de aprovação do líder), sem duplicar."""
    membro, _ = MembrosEquipe.objects.get_or_create(usuario=usuario, equipe=equipe)
    return membro


def cancelar_candidatura(usuario, equipe):
    """Cancela uma candidatura ainda não aprovada."""
    apagadas, _ = MembrosEquipe.objects.filter(usuario=usuario, equipe=equipe, aprovado=False).delete()
    if not apagadas:
        raise RegraDeNegocio("Você não tem candidatura pendente nesta equipe.", code='sem_candidatura')


def aprovar_candidatura(membro):
    """Aprova a entrada na equipe e avisa a pessoa. Devolve False se já estava aprovada."""
    if membro.aprovado:
        return False
    membro.aprovado = True
    membro.save()
    notificar_push(
        membro.usuario_id, *mensagens_push.entrada_na_equipe(membro.equipe),
        tipo='membro_aprovado', purpose=Notification.PURPOSE_MEMBER_APPROVED,
    )
    return True


def recusar_candidatura(membro):
    """Recusa uma candidatura pendente (sem aviso, como no site)."""
    if membro.aprovado:
        raise RegraDeNegocio("Esta pessoa já é membro da equipe.", code='ja_membro')
    membro.delete()
