from django.utils import timezone

from escala.models import Desistencia, Escala, Funcao, SolicitacaoTroca
from escalaconnect import mensagens_push
from escalaconnect.push import notificar_push
from escalaconnect.regras import RegraDeNegocio
from evento.models import Notification

from .models import Equipe, Lideranca, MembrosEquipe


def equipes_lideradas(usuario):
    """Equipes que o usuário pode gerenciar (todas, se for staff/superuser)."""
    if usuario.is_superuser or usuario.is_staff:
        return Equipe.objects.all()
    return Equipe.objects.filter(lideranca__usuario=usuario).distinct()


def pendencias_do_lider(usuario):
    """Impedimentos, trocas, ofertas para vagas e candidaturas esperando o líder.

    Impedimentos e trocas seguem o mesmo critério do painel do site.
    """
    from escala import services as escala_services  # escala.services importa equipe.models

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
        'ofertas': (
            escala_services.ofertas_pendentes()
            .filter(escala__funcao__equipe__in=equipes)
            .select_related('escala__evento', 'escala__funcao__equipe', 'candidato')
            .order_by('escala__evento__data_inicio', 'data_candidatura')
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


# ── Gestão da equipe pelo líder (app): funções, lideranças e integrantes ──
# Mesmos papéis do site: o líder mexe em funções e integrantes e remove lideranças;
# renomear a equipe e adicionar líderes continuam só com o admin.

def _nome_de_funcao(equipe, nome, exceto=None):
    nome = (nome or '').strip()
    if not nome:
        raise RegraDeNegocio("Informe o nome da função.", code='nome_vazio')
    repetidas = Funcao.objects.filter(equipe=equipe, nome__iexact=nome)
    if exceto is not None:
        repetidas = repetidas.exclude(pk=exceto.pk)
    if repetidas.exists():
        raise RegraDeNegocio(f"A equipe já tem a função {nome}.", code='funcao_repetida')
    return nome


def criar_funcao(equipe, nome):
    return Funcao.objects.create(equipe=equipe, nome=_nome_de_funcao(equipe, nome))


def renomear_funcao(funcao, nome):
    funcao.nome = _nome_de_funcao(funcao.equipe, nome, exceto=funcao)
    funcao.save(update_fields=['nome'])
    return funcao


def excluir_funcao(funcao):
    """Só exclui função sem nenhuma escala: apagar levaria junto o histórico de quem serviu."""
    if Escala.objects.filter(funcao=funcao).exists():
        raise RegraDeNegocio(
            f"A função {funcao.nome} já tem escalas. Para não perder o histórico, peça ao admin para excluir.",
            code='funcao_com_escalas')
    funcao.delete()


def remover_lideranca(lideranca):
    """Tira alguém da liderança (continua integrante). A equipe não fica sem líder."""
    if not Lideranca.objects.filter(equipe_id=lideranca.equipe_id).exclude(pk=lideranca.pk).exists():
        raise RegraDeNegocio("A equipe precisa ter pelo menos um líder.", code='ultimo_lider')
    lideranca.delete()


def adicionar_integrante(equipe, usuario):
    """Coloca a pessoa na equipe já aprovada, como no site. Candidatura pendente é aprovada (com aviso)."""
    membro, criado = MembrosEquipe.objects.get_or_create(equipe=equipe, usuario=usuario, defaults={'aprovado': True})
    if not criado:
        if membro.aprovado:
            raise RegraDeNegocio("Essa pessoa já faz parte da equipe.", code='ja_membro')
        aprovar_candidatura(membro)
    return membro


def remover_integrante(membro):
    """Tira a pessoa da equipe. Líder sai da liderança primeiro; escalas já feitas continuam."""
    if Lideranca.objects.filter(equipe_id=membro.equipe_id, usuario_id=membro.usuario_id).exists():
        raise RegraDeNegocio("Essa pessoa é líder da equipe. Remova a liderança primeiro.", code='e_lider')
    membro.delete()
