from django.contrib import admin
from .models import Equipe, MembrosEquipe, Lideranca

@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ['nome']

@admin.register(MembrosEquipe)
class MembrosEquipeAdmin(admin.ModelAdmin):
    list_display = ['equipe', 'usuario', 'aprovado']
    list_filter = ['equipe']

@admin.register(Lideranca)
class LiderancaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'equipe']
    list_filter = ['equipe']
