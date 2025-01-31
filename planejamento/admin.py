from django.contrib import admin
from .models import Planejamento, PlanejamentoFuncao

class PlanejamentoFuncaoInline(admin.TabularInline):
    model = PlanejamentoFuncao
    extra = 1

@admin.register(Planejamento)
class PlanejamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'data_cadastro', 'data_atualizacao')
    search_fields = ('nome',)
    inlines = [PlanejamentoFuncaoInline]

@admin.register(PlanejamentoFuncao)
class PlanejamentoFuncaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'planejamento', 'funcao')
