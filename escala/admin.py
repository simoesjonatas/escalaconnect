from django.contrib import admin
from .models import Desistencia, Escala, EscalaFixa, EscalaFixaItem, Funcao, Rendimento, SolicitacaoTroca

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



class EscalaFixaItemInline(admin.TabularInline):
    model = EscalaFixaItem
    extra = 0


@admin.register(EscalaFixa)
class EscalaFixaAdmin(admin.ModelAdmin):
    list_display = ['equipe', 'ativa', 'atualizada_em']
    inlines = [EscalaFixaItemInline]
