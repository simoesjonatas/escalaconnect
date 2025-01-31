from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Usuario

class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'telefone', 'cpf', 'is_active')
    search_fields = ('username', 'email', 'cpf')
    ordering = ('username',)

admin.site.register(Usuario, UsuarioAdmin)
