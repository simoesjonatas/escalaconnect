from disponivel.models import Disponivel
from escalaconnect.periodos import Periodos

from .models import Ocupado

indisponibilidades = Periodos(
    Ocupado, Disponivel,
    "Existe uma disponibilidade registrada que conflita com este período de indisponibilidade.",
)
