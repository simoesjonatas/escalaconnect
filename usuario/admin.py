from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Usuario, PasswordResetRequest

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


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'reset_at', 'is_used', 'hash_valido',  'created_at',)
    list_filter = ('is_used', 'created_at', 'reset_at')
    search_fields = ('usuario__username', 'usuario__email', 'hash')
    readonly_fields = ('usuario', 'hash', 'created_at', 'reset_at', 'is_used')

    def hash_valido(self, obj):
        return obj.hash_valido()
    hash_valido.boolean = True
    hash_valido.short_description = 'Hash válido?'

admin.site.register(Usuario, UsuarioAdmin)
