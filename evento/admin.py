from django.contrib import admin
from .models import Evento, Disponibilidade
from .models import Notification, NotificationAttempt

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'data_inicio', 'data_fim']
    list_filter = ['data_inicio']
    search_fields = ['nome']

@admin.register(Disponibilidade)
class DisponibilidadeAdmin(admin.ModelAdmin):
    list_display = ['evento', 'usuario']
    list_filter = ['evento']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "escala",
        "channel",
        "purpose",
        "total_attempts",
        "success_count",
        "last_status",
        "last_sent_at",
    )
    list_filter = ("channel", "purpose", "last_status")
    search_fields = ("usuario__username", "usuario__email", "escala__id")
    list_select_related = ("usuario", "escala")


@admin.register(NotificationAttempt)
class NotificationAttemptAdmin(admin.ModelAdmin):
    # mostra usuário, email, escala, canal e propósito direto na lista
    list_display = (
        "id",
        "user",          # -> notification.usuario
        "user_email",    # -> notification.usuario.email
        "escala_ref",    # -> notification.escala
        "channel_ref",   # -> notification.channel (ou get_channel_display)
        "purpose_ref",   # -> notification.purpose (ou get_purpose_display)
        "status",
        "created_at",
    )
    # filtros úteis, inclusive pelos campos da FK
    list_filter = (
        "status",
        "notification__channel",
        "notification__purpose",
    )
    # busca por usuário/escala
    search_fields = (
        "notification__usuario__username",
        "notification__usuario__email",
        "notification__escala__id",
    )
    date_hierarchy = "created_at"
    # evita N+1
    list_select_related = (
        "notification",
        "notification__usuario",
        "notification__escala",
    )

    # --- colunas derivadas ---
    @admin.display(description="Usuário", ordering="notification__usuario__username")
    def user(self, obj):
        return obj.notification.usuario

    @admin.display(description="E-mail", ordering="notification__usuario__email")
    def user_email(self, obj):
        u = obj.notification.usuario
        return getattr(u, "email", "") if u else ""

    @admin.display(description="Escala", ordering="notification__escala__id")
    def escala_ref(self, obj):
        return obj.notification.escala

    @admin.display(description="Canal", ordering="notification__channel")
    def channel_ref(self, obj):
        n = obj.notification
        # se Notification.channel tem choices, use get_channel_display()
        return n.get_channel_display() if hasattr(n, "get_channel_display") else n.channel

    @admin.display(description="Propósito", ordering="notification__purpose")
    def purpose_ref(self, obj):
        n = obj.notification
        # se Notification.purpose tem choices, use get_purpose_display()
        return n.get_purpose_display() if hasattr(n, "get_purpose_display") else n.purpose