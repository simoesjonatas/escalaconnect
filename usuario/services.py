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
