from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from escala.models import Escala
from escalaconnect.push import notificar_push, quando
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
        instance.usuario_id,
        'Você foi escalado',
        f'{evento.nome} · {quando(evento)} · {instance.funcao.nome}',
        tipo='escalado', purpose=Notification.PURPOSE_ASSIGNED, escala_id=instance.pk,
    )
