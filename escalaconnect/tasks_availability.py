# escalaconnect/tasks_availability.py
from __future__ import annotations

from celery import shared_task
from datetime import date, datetime, time
import calendar


from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse, NoReverseMatch
from django.utils import timezone, formats

from usuario.models import Usuario
from escala.models import Escala
from equipe.models import Equipe
from evento.models import Evento, Notification, NotificationAttempt
from disponivel.models import Disponivel
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count


# ----------------- helpers -----------------
def _site_url() -> str:
    return getattr(settings, "SITE_URL", "https://connect.pibvp.org.br").rstrip("/")

def _abs_url(path: str) -> str:
    return f"{_site_url()}{path}"

def _month_bounds(ano: int, mes: int) -> tuple[datetime, datetime, date, date]:
    """Retorna (dt_inicial, dt_final, d_inicial, d_final) para o mês."""
    d_first = date(ano, mes, 1)
    d_last = date(ano, mes, calendar.monthrange(ano, mes)[1])
    # janelas em DateTime para facilitar __gte/__lte
    tz = timezone.get_current_timezone()
    dt_first = timezone.make_aware(datetime.combine(d_first, time.min), tz)
    dt_last  = timezone.make_aware(datetime.combine(d_last,  time.max), tz)
    return dt_first, dt_last, d_first, d_last

def _build_disponibilidade_url(ano: int, mes: int) -> str:
    """
    Ajuste o reverse para a sua rota real.
    Tenta uma rota nomeada e cai para um fallback amigável.
    """
    for name in ("disponibilidade_mes", "registrar_disponibilidade_mes", "disponivel_mes"):
        try:
            path = reverse(name, kwargs={"ano": ano, "mes": mes})
            return _abs_url(path)
        except NoReverseMatch:
            continue
    # fallback simples caso não exista URL nomeada ainda:
    return f"{_site_url()}/disponivel/{ano}/{mes}/"
# -------------------------------------------


@shared_task(rate_limit="120/m")
def disparar_pedido_disponibilidades(ano: int, mes: int, equipe_id: int | None = None, lider_nome: str = "Líder"):
    """
    Envia e-mail pedindo cadastro de disponibilidades para o mês/ano.
    Só envia para usuários que AINDA NÃO registraram nenhuma Disponibilidade
    para eventos dentro do mês informado.

    Se equipe_id for informado, limita o universo aos usuários que já serviram
    (têm Escala) nessa equipe em qualquer momento.
    """
    # --- janela do mês ---
    dt_first, dt_last, d_first, d_last = _month_bounds(ano, mes)
    mes_legivel = formats.date_format(d_first, "F \\d\\e Y", use_l10n=True)
    # disponibilidades_url = _build_disponibilidade_url(ano, mes)
    disponibilidades_url = "https://connect.pibvp.org.br/login/?next=/api/free/registrar-disponibilidade/por-evento/"

    # --- eventos do mês (qualquer sobreposição com o mês) ---
    eventos_mes = Evento.objects.filter(
        data_inicio__date__lte=d_last,
        data_fim__date__gte=d_first,
    ).values_list("id", flat=True)

    # Se não há eventos no mês, não faz sentido cobrar disponibilidade
    if not eventos_mes:
        return {"usuarios_faltantes": 0, "emails_enviados": 0, "obs": "sem eventos no mês"}

    # --- universo de usuários ---
    usuarios_qs = Usuario.objects.filter(is_active=True)

    # Limitar ao conjunto base (apenas membros aprovados da equipe, se houver equipe_id)
    if equipe_id:
        try:
            # TENTA usar um modelo de membresia explícito
            MembroEquipe = apps.get_model("equipe", "MembroEquipe")
            base_user_ids = (
                MembroEquipe.objects
                .filter(equipe_id=equipe_id, aprovado=True)
                .values_list("usuario_id", flat=True)
            )
        except LookupError:
            # FALLBACK: quem já serviu nessa equipe (histórico de Escala)
            base_user_ids = (
                Usuario.objects
                .filter(escala__funcao__equipe_id=equipe_id)
                .values_list("id", flat=True)
                .distinct()
            )

        usuarios_qs = usuarios_qs.filter(id__in=base_user_ids)
    

    # ===> Quem JÁ tem disponibilidade no mês X (qualquer sobreposição com a janela do mês)
    # regra de sobreposição: (disp.início <= fim_do_mês) && (disp.fim >= início_do_mês)
    usuarios_com_disp_ids = (
        Disponivel.objects
        .filter(
            data_inicio__lte=dt_last,
            data_fim__gte=dt_first,
        )
        .values_list("usuario_id", flat=True)
        .distinct()
    )

    # print("DEBUG eventos_mes:", list(eventos_mes))
    # print("DEBUG usuarios_com_disp_ids:", list(usuarios_com_disp_ids))

    # --- faltantes: sem disponibilidade e com e-mail válido ---
    faltantes_qs = (
        usuarios_qs
        .exclude(id__in=usuarios_com_disp_ids)
        .exclude(email__isnull=True)
        .exclude(email__exact="")
    )

    # Para exibir nome da equipe (opcional)
    equipe_nome = None
    if equipe_id:
        try:
            equipe_nome = Equipe.objects.get(pk=equipe_id).nome
        except Equipe.DoesNotExist:
            equipe_nome = None

    enviados = 0
    total_faltantes = faltantes_qs.count()

    # print("DEBUG eventos_mes count:", len(list(eventos_mes)))
    # print("DEBUG faltantes:", total_faltantes)
    # for u in faltantes_qs:
    #     print(" - ", u.get_username(), u.email)

    for u in faltantes_qs:
        contexto = {
            "usuario_nome": (getattr(u, "first_name", "") or u.get_username()),
            "lider_nome": lider_nome,
            "equipe_nome": equipe_nome,
            "mes_legivel": mes_legivel,
            "disponibilidades_url": disponibilidades_url,
        }

        assunto = f"Precisamos das suas disponibilidades – {mes_legivel}"
        corpo_html = render_to_string("email/lembrar_disponibilidade.html", contexto)
        corpo_txt = f"{contexto['usuario_nome']}, cadastre suas disponibilidades: {disponibilidades_url}"

        # --- log (Notification/Attempt) ---
        notif, _ = Notification.objects.get_or_create(
            escala=None,  # lembrete não está vinculado a uma escala específica
            usuario=u,
            channel=Notification.CHANNEL_EMAIL,
            purpose=Notification.PURPOSE_AVAILABILITY,
            defaults={"last_status": "queued"},
        )

        # Throttle: evita repetir o lembrete em menos de 24h para o mesmo usuário
        if notif.last_sent_at and (timezone.now() - notif.last_sent_at).total_seconds() < 24 * 3600:
            NotificationAttempt.objects.create(
                notification=notif,
                status="skipped",
                error_message="Throttle: lembrete enviado nas últimas 24h",
                response_metadata={"reason": "availability_throttle_24h", "mes": mes, "ano": ano},
            )
            continue

        try:
            msg = EmailMultiAlternatives(subject=assunto, body=corpo_txt, to=[u.email])
            msg.attach_alternative(corpo_html, "text/html")
            ok = msg.send()

            status = "sent" if ok else "error"
            err = "" if ok else "EmailBackend retornou 0"

            NotificationAttempt.objects.create(
                notification=notif,
                status=status,
                error_message=err,
                response_metadata={"send_result": ok, "mes": mes, "ano": ano},
            )

            notif.total_attempts += 1
            if status == "sent":
                notif.success_count += 1
                notif.last_sent_at = timezone.now()
            notif.last_status = status
            notif.last_error = err
            notif.last_response = str({"send_result": ok})
            notif.save(update_fields=[
                "total_attempts", "success_count", "last_sent_at",
                "last_status", "last_error", "last_response", "updated_at"
            ])

            if ok:
                enviados += 1

        except Exception as e:
            NotificationAttempt.objects.create(
                notification=notif,
                status="error",
                error_message=str(e),
                response_metadata={"mes": mes, "ano": ano},
            )
            notif.total_attempts += 1
            notif.last_status = "error"
            notif.last_error = str(e)
            notif.save(update_fields=["total_attempts", "last_status", "last_error", "updated_at"])

    return {"usuarios_faltantes": total_faltantes, "emails_enviados": enviados}
