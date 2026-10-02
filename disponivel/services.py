from escalaconnect.periodos import Periodos
from ocupado.models import Ocupado

from .models import Disponivel

disponibilidades = Periodos(
    Disponivel, Ocupado,
    "Existe uma indisponibilidade registrada que conflita com este período de disponibilidade.",
)
