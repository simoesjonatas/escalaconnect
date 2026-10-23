from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from equipe.models import Lideranca, MembrosEquipe
from escala.models import Desistencia, Escala, SolicitacaoTroca
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
