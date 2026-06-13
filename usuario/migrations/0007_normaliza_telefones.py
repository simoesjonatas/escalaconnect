from django.db import migrations


def _normalizar(value):
    """Mesma regra de usuario.utils.normalizar_telefone (duplicada de propósito:
    migrações devem ser autossuficientes e imunes a mudanças futuras no app)."""
    digitos = ''.join(filter(str.isdigit, value))
    if len(digitos) in (12, 13) and digitos.startswith('55'):
        digitos = digitos[2:]
    return digitos


def normalizar_telefones(apps, schema_editor):
    Usuario = apps.get_model('usuario', 'Usuario')
    usuarios = Usuario.objects.exclude(telefone__isnull=True).exclude(telefone='')
    alterados = []
    for usuario in usuarios:
        normalizado = _normalizar(usuario.telefone)
        if normalizado != usuario.telefone:
            usuario.telefone = normalizado
            alterados.append(usuario)
    if alterados:
        Usuario.objects.bulk_update(alterados, ['telefone'])


def noop(apps, schema_editor):
    # Sem reverso: a formatação original não é recuperável (nem necessária).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('usuario', '0006_usuario_termo_aceito_em_alter_usuario_aniversario_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_telefones, noop),
    ]
