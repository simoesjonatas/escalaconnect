# Generated by Django 5.1.5 on 2025-03-15 14:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('escala', '0005_alter_solicitacaotroca_aprovada'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitacaotroca',
            name='data_aprovacao',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
