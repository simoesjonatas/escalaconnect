import re

from django.core.cache import cache
from django.db import IntegrityError
from django.utils import timezone

from escalaconnect.regras import RegraDeNegocio


def termo_pendente(user):
    """True se o usuário ainda precisa aceitar o termo do voluntário (staff é isento)."""
    return not (user.is_staff or user.is_superuser) and user.termo_aceito_em is None


def registrar_atividade(user):
    """Registra a última atividade e a atividade diária do usuário.

    Grava no banco no máximo uma vez por minuto por usuário (throttle via cache)
    para não adicionar escrita a cada request. Usado pelo site (AtividadeMiddleware)
    e pela API do app (autenticação por token).
    """
    chave = f'atividade-usuario-{user.pk}'
    if cache.get(chave) is not None:
        return
    cache.set(chave, 1, 60)
    from .models import AtividadeDiaria, Usuario
    agora = timezone.now()
    Usuario.objects.filter(pk=user.pk).update(ultima_atividade=agora)
    try:
        AtividadeDiaria.objects.get_or_create(usuario_id=user.pk, data=timezone.localdate(agora))
    except IntegrityError:
        # Corrida entre workers: o registro do dia já existe.
        pass


def aceitar_termo(user):
    """Registra o aceite do termo de compromisso do voluntário."""
    user.termo_aceito_em = timezone.now()
    user.save(update_fields=['termo_aceito_em'])


def pedir_redefinicao_senha(cpf, aniversario):
    """Esqueci minha senha (site e app): acha a conta por CPF e data de nascimento e manda
    por e-mail o link para criar uma senha nova. Devolve o usuário encontrado."""
    from .mail import enviar_email_redefinicao_senha
    from .models import PasswordResetRequest, Usuario

    usuario = Usuario.objects.filter(cpf=re.sub(r'[^0-9]', '', cpf), aniversario=aniversario).first()
    if usuario is None:
        raise RegraDeNegocio('Dados não encontrados. Verifique seu CPF e data de nascimento.',
                             code='dados_nao_encontrados')
    if not usuario.email:
        raise RegraDeNegocio('Sua conta não tem e-mail cadastrado. Peça ao líder da sua equipe para redefinir sua senha.',
                             code='sem_email')
    # Só o link mais recente vale.
    PasswordResetRequest.objects.filter(usuario=usuario, is_used=False).update(is_used=True)
    enviar_email_redefinicao_senha(usuario.email, PasswordResetRequest.objects.create(usuario=usuario))
    return usuario


def mascarar_email(email):
    """jonatas@gmail.com -> jo*****@gmail.com, para confirmar o destino sem expor o endereço."""
    nome, _, dominio = email.partition('@')
    return f"{nome[:2]}{'*' * max(len(nome) - 2, 3)}@{dominio}"


# ── Cadastro e exclusão da conta (site e app) ──

def gerar_username(first_name, last_name):
    """'nome.sobrenome'; se já existir, 'nome.sobrenome2', 'nome.sobrenome3'..."""
    from .models import Usuario
    base = f'{first_name}.{last_name}'.lower().replace(' ', '')
    username, n = base, 1
    while Usuario.objects.filter(username__iexact=username).exists():
        n += 1
        username = f'{base}{n}'
    return username


def excluir_conta(usuario):
    """O próprio voluntário exclui a conta (exigência da LGPD e das lojas de apps).

    Os dados pessoais são apagados e a conta fica inativa, mas as escalas que já
    aconteceram continuam contando, em nome de "Ex-voluntário". As escalas futuras
    viram vaga e a liderança de cada equipe recebe um aviso.
    """
    from django.db import transaction

    from api.models import Aviso, Device
    from disponivel.models import Disponivel
    from equipe.models import Lideranca, MembrosEquipe
    from escala.models import Desistencia, Escala, Rendimento, SolicitacaoTroca
    from evento.models import Disponibilidade, Notification
    from escalaconnect import mensagens_push
    from escalaconnect.push import notificar_push
    from ocupado.models import Ocupado

    from .models import AtividadeDiaria, PasswordResetRequest, RegistroLogin

    if usuario.is_staff or usuario.is_superuser:
        raise RegraDeNegocio(
            'Contas de administração não podem ser excluídas por aqui. Fale com outro administrador.',
            code='conta_admin',
        )

    nome = usuario.get_full_name() or usuario.username
    with transaction.atomic():
        # Escalas futuras viram vaga; a liderança de cada equipe é avisada (antes de sair das lideranças).
        futuras = list(
            Escala.objects.filter(usuario=usuario, evento__data_inicio__gt=timezone.now())
            .select_related('evento', 'funcao__equipe')
        )
        por_equipe = {}
        for escala in futuras:
            por_equipe.setdefault(escala.funcao.equipe, []).append(escala)
        Escala.objects.filter(pk__in=[e.pk for e in futuras]).update(
            usuario=None, confirmada=False, data_confirmacao=None)

        for modelo, campo in [
            (MembrosEquipe, 'usuario'), (Lideranca, 'usuario'), (Disponibilidade, 'usuario'),
            (Disponivel, 'usuario'), (Ocupado, 'usuario'), (Desistencia, 'usuario'),
            (SolicitacaoTroca, 'solicitante'), (Rendimento, 'candidato'), (Device, 'usuario'),
            (Aviso, 'usuario'), (Notification, 'usuario'), (RegistroLogin, 'usuario'),
            (AtividadeDiaria, 'usuario'), (PasswordResetRequest, 'usuario'),
        ]:
            modelo.objects.filter(**{campo: usuario}).delete()
        usuario.auth_token_set.all().delete()

        usuario.username = f'ex-voluntario-{usuario.pk}'
        usuario.first_name = 'Ex-voluntário'
        usuario.last_name = ''
        usuario.email = ''
        usuario.telefone = None
        usuario.aniversario = None
        usuario.batismo = None
        usuario.cpf = f'x{usuario.pk}'[:11]  # único e nunca um CPF válido
        usuario.termo_aceito_em = None
        usuario.ultima_atividade = None
        usuario.last_login = None
        usuario.is_active = False
        usuario.set_unusable_password()
        usuario.save()

        for equipe, escalas in por_equipe.items():
            lideres = Lideranca.objects.filter(equipe=equipe).values_list('usuario_id', flat=True).distinct()
            for lider_id in lideres:
                notificar_push(
                    lider_id, *mensagens_push.lider_vagas_de_quem_saiu(nome, escalas),
                    tipo='pendencia_lider', purpose=Notification.PURPOSE_LEADER_PENDING,
                    escala_id=escalas[0].pk if len(escalas) == 1 else None,
                )
