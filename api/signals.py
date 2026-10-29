from datetime import timedelta

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from equipe.models import Lideranca, MembrosEquipe
from escala import services as escala_services
from escala.models import Desistencia, Escala, Rendimento, SolicitacaoTroca
from escalaconnect import mensagens_push
from escalaconnect.push import notificar_push
from evento.models import Notification


@receiver(pre_save, sender=Escala)
def guardar_usuario_anterior(sender, instance, **kwargs):
    # A atribuição acontece em vários lugares (views do líder, auto-escalar, forms);
    # o signal cobre todos sem espalhar chamadas de push pelo site.
    instance._usuario_anterior_id = (
        Escala.objects.filter(pk=instance.pk).values_list('usuario_id', flat=True).first()
        if instance.pk else None
    )


@receiver(post_save, sender=Escala)
def avisar_quem_foi_escalado(sender, instance, **kwargs):
    if not instance.usuario_id or instance.usuario_id == getattr(instance, '_usuario_anterior_id', None):
        return
    evento = instance.evento
    if evento.data_fim < timezone.now():
        return
    notificar_push(
        instance.usuario_id, *mensagens_push.escalado(instance),
        tipo='escalado', purpose=Notification.PURPOSE_ASSIGNED, escala_id=instance.pk,
    )


@receiver(post_save, sender=Escala)
def encerrar_ofertas_da_vaga(sender, instance, **kwargs):
    # Quem preencheu a vaga (app, site ou auto-escalar) encerra as ofertas que ainda estavam abertas.
    if instance.usuario_id and instance.usuario_id != getattr(instance, '_usuario_anterior_id', None):
        escala_services.encerrar_ofertas(instance, instance.usuario_id)


# ── Pendências para o líder ──

def _avisar_lideres(equipe, autor_id, mensagem, escala_id=None):
    lideres = (
        Lideranca.objects.filter(equipe=equipe).exclude(usuario_id=autor_id)
        .values_list('usuario_id', flat=True).distinct()
    )
    for lider_id in lideres:
        notificar_push(
            lider_id, *mensagem,
            # 'pendencia_lider' abre a aba Liderança no app.
            tipo='pendencia_lider', purpose=Notification.PURPOSE_LEADER_PENDING, escala_id=escala_id,
        )


@receiver(post_save, sender=Desistencia)
def avisar_lider_impedimento(sender, instance, created, **kwargs):
    if created and not instance.aprovada:
        _avisar_lideres(instance.escala.equipe, instance.usuario_id,
                        mensagens_push.lider_impedimento(instance), escala_id=instance.escala_id)


@receiver(post_save, sender=SolicitacaoTroca)
def avisar_lider_troca(sender, instance, created, **kwargs):
    if created and not instance.aprovada:
        _avisar_lideres(instance.escala_origem.equipe, instance.solicitante_id,
                        mensagens_push.lider_troca(instance), escala_id=instance.escala_origem_id)


@receiver(post_save, sender=MembrosEquipe)
def avisar_lider_candidatura(sender, instance, created, **kwargs):
    if created and not instance.aprovado:
        _avisar_lideres(instance.equipe, instance.usuario_id, mensagens_push.lider_candidatura(instance))


# Várias pessoas se oferecendo para o mesmo culto não devem tocar o celular do líder a cada uma.
JANELA_DE_OFERTAS = timedelta(hours=12)


@receiver(post_save, sender=Rendimento)
def avisar_lider_oferta(sender, instance, created, **kwargs):
    """Primeira oferta de um culto: push na hora. As seguintes, por 12h, só atualizam o mesmo
    aviso da caixa ("3 pessoas querem servir") e o deixam como não lido, sem novo push."""
    if not created or instance.aprovada:
        return
    from api.models import Aviso
    from escala.services import ofertas_pendentes

    evento = instance.escala.evento
    lideres = (
        Lideranca.objects.filter(equipe=instance.escala.equipe).exclude(usuario_id=instance.candidato_id)
        .values_list('usuario_id', flat=True).distinct()
    )
    for lider_id in lideres:
        recente = Aviso.objects.filter(
            usuario_id=lider_id, purpose=Notification.PURPOSE_LEADER_OFFER, escala__evento=evento,
            criado_em__gte=timezone.now() - JANELA_DE_OFERTAS,
        ).first()
        if recente is None:
            notificar_push(
                lider_id, *mensagens_push.lider_oferta(instance),
                # 'oferta_lider' abre a tela do culto no app (quem se ofereceu e quem está disponível).
                tipo='oferta_lider', purpose=Notification.PURPOSE_LEADER_OFFER, escala_id=instance.escala_id,
            )
            continue
        quantas = ofertas_pendentes().filter(
            escala__evento=evento, escala__funcao__equipe__lideranca__usuario_id=lider_id).distinct().count()
        recente.titulo, recente.corpo = mensagens_push.lider_ofertas(evento, quantas)
        recente.lido_em = None
        recente.save(update_fields=['titulo', 'corpo', 'lido_em'])
