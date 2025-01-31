from django.contrib import admin
from .models import Escala, Funcao, SolicitacaoTroca, Desistencia, Rendimento

@admin.register(Escala)
class EscalaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'funcao', 'evento', 'confirmada']
    list_filter = ['evento', 'confirmada']

@admin.register(Funcao)
class FuncaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'equipe']
    list_filter = ['equipe']

@admin.register(SolicitacaoTroca)
class SolicitacaoTrocaAdmin(admin.ModelAdmin):
    list_display = ['solicitante', 'escala_origem', 'escala_destino', 'aprovada']
    list_filter = ['aprovada', 'tipo_solicitacao']

@admin.register(Desistencia)
class DesistenciaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'escala', 'aprovada']
    list_filter = ['aprovada']

@admin.register(Rendimento)
class RendimentoAdmin(admin.ModelAdmin):
    list_display = ['candidato', 'escala', 'aprovada']
    list_filter = ['aprovada']
