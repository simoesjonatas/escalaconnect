from django.utils import timezone

from disponivel.models import Disponivel
from escala.models import Escala


def pendencias_home(usuario):
    """Pendências do voluntário mostradas na tela inicial (site e app)."""
    futuras = Escala.objects.filter(usuario=usuario, evento__data_inicio__gte=timezone.now())
    return {
        'tem_disponibilidade': Disponivel.objects.filter(usuario=usuario).exists(),
        # Só escalas futuras: a agenda (.ics) e o botão de baixar consideram de hoje pra frente.
        'tem_escalas': futuras.exists(),
        'escalas_pendentes': futuras.filter(confirmada=False).count(),
        # Contato incompleto: sem e-mail, ou telefone vazio/sem DDD (menos de 10 dígitos).
        'falta_email': not usuario.email,
        'falta_telefone': len(usuario.telefone or '') < 10,
    }
