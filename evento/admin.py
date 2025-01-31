from django.contrib import admin
from .models import Evento, Disponibilidade

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'data_inicio', 'data_fim']
    list_filter = ['data_inicio']
    search_fields = ['nome']

@admin.register(Disponibilidade)
class DisponibilidadeAdmin(admin.ModelAdmin):
    list_display = ['evento', 'usuario']
    list_filter = ['evento']
