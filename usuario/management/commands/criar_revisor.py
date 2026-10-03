"""Cria (ou renova) o usuário de demonstração usado na revisão das lojas (Apple/Google).

Uso: python manage.py criar_revisor [--senha SENHA]

Idempotente: pode rodar de novo antes de cada envio para revisão. Mantém o usuário
"revisor" fora das equipes reais: ele entra numa equipe própria, com eventos
privados dessa equipe (invisíveis aos demais voluntários) nas próximas semanas,
com uma escala a confirmar, uma confirmada e uma vaga em aberto para a qual ele
tem disponibilidade. Assim o revisor consegue exercitar todos os fluxos do app.
"""
import secrets
import string
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from disponivel.models import Disponivel
from equipe.models import Equipe, MembrosEquipe
from escala.models import Escala, Funcao
from evento.models import Evento

USERNAME = 'revisor'
EQUIPE = 'Equipe de demonstração'
FUNCAO = 'Recepção'
EVENTO = 'Culto de demonstração'
CPF_FICTICIO = '00000000191'  # válido pelos dígitos verificadores, mas inexistente


def proximos_domingos(quantidade):
    hoje = timezone.localtime()
    dias_ate_domingo = (6 - hoje.weekday()) % 7 or 7
    primeiro = (hoje + timedelta(days=dias_ate_domingo)).replace(hour=9, minute=45, second=0, microsecond=0)
    return [primeiro + timedelta(weeks=i) for i in range(quantidade)]


class Command(BaseCommand):
    help = 'Cria ou renova o usuário "revisor" com equipe, eventos e escalas de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument('--senha', help='Senha do revisor (padrão: gera uma nova e mostra na tela).')

    @transaction.atomic
    def handle(self, *args, **opcoes):
        User = get_user_model()
        senha = opcoes['senha'] or ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        revisor, criado = User.objects.get_or_create(
            username=USERNAME,
            defaults={'first_name': 'Revisor', 'last_name': 'da Loja', 'email': 'revisor@example.com',
                      'cpf': CPF_FICTICIO, 'telefone': '21999999999'},
        )
        revisor.set_password(senha)
        revisor.is_first_login = False
        revisor.termo_aceito_em = revisor.termo_aceito_em or timezone.now()
        revisor.is_active = True
        revisor.save()

        equipe, _ = Equipe.objects.get_or_create(nome=EQUIPE)
        funcao, _ = Funcao.objects.get_or_create(equipe=equipe, nome=FUNCAO)
        MembrosEquipe.objects.update_or_create(usuario=revisor, equipe=equipe, defaults={'aprovado': True})

        # Renova: apaga os eventos de demonstração antigos (e, em cascata, escalas e disponibilidades).
        Evento.objects.filter(equipe=equipe, nome=EVENTO).delete()

        a_confirmar, confirmada, vaga = [
            Evento.objects.create(nome=EVENTO, data_inicio=inicio, data_fim=inicio + timedelta(hours=2), equipe=equipe)
            for inicio in proximos_domingos(3)
        ]
        Escala.objects.create(evento=a_confirmar, funcao=funcao, usuario=revisor)
        Escala.objects.create(evento=confirmada, funcao=funcao, usuario=revisor, confirmada=True,
                              data_confirmacao=timezone.now())
        Escala.objects.create(evento=vaga, funcao=funcao)  # vaga em aberto
        Disponivel.objects.create(usuario=revisor, evento=vaga, data_inicio=vaga.data_inicio, data_fim=vaga.data_fim)

        self.stdout.write(self.style.SUCCESS(f'Usuário "{USERNAME}" {"criado" if criado else "renovado"}.'))
        self.stdout.write(f'  usuário: {USERNAME}')
        self.stdout.write(f'  senha:   {senha}')
        self.stdout.write(f'  equipe:  {EQUIPE} (eventos privados nos próximos 3 domingos)')
        self.stdout.write('Informe usuário e senha nas notas de revisão da loja.')
