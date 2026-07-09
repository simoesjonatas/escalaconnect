from django.contrib import admin
from .models import Disponivel

@admin.register(Disponivel)
class DisponivelAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'evento', 'data_inicio', 'data_fim', 'data_cadastro', 'data_atualizacao']
    list_filter = ['data_inicio', 'evento']
    search_fields = [
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
        'usuario__email',
        'evento__nome',
    ]
    date_hierarchy = 'data_inicio'
    list_select_related = ['usuario', 'evento']
    ordering = ['-data_inicio']
