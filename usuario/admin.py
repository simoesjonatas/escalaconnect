from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Usuario

class UsuarioAdmin(UserAdmin):
    model = Usuario
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email', 'telefone', 'aniversario', 'cpf')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name', 'telefone', 'aniversario', 'cpf'),
        }),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'telefone', 'cpf')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'cpf')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    ordering = ('username',)

admin.site.register(Usuario, UsuarioAdmin)
