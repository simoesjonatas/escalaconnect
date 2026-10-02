from escalaconnect.regras import RegraDeNegocio

from .models import Equipe, MembrosEquipe


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
