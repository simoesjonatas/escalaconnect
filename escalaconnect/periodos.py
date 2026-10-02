from datetime import timedelta

from django.utils import timezone

from evento.models import Evento

from .regras import RegraDeNegocio


class Periodos:
    """Regras comuns a disponibilidades (Disponivel) e indisponibilidades (Ocupado).

    Os dois models têm a mesma forma (usuário, início, fim, evento opcional) e um
    não pode se sobrepor ao outro. Instâncias em disponivel/services.py e
    ocupado/services.py, usadas pelo site e pela API do app.
    """

    JANELA_EVENTOS = timedelta(days=60)

    def __init__(self, modelo, conflitante, mensagem_conflito):
        self.modelo = modelo
        self.conflitante = conflitante
        self.mensagem_conflito = mensagem_conflito

    def do_usuario(self, usuario):
        return self.modelo.objects.filter(usuario=usuario)

    def futuros(self, usuario):
        """Períodos do usuário de hoje (fuso local) em diante."""
        hoje = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.do_usuario(usuario).filter(data_inicio__gte=hoje, data_fim__gte=hoje)

    def validar(self, usuario, data_inicio, data_fim):
        if data_fim <= data_inicio:
            raise RegraDeNegocio("O fim do período precisa ser depois do início.", code='periodo_invalido')
        conflitos = self.conflitante.objects.filter(
            usuario=usuario, data_inicio__lt=data_fim, data_fim__gt=data_inicio)
        if conflitos.exists():
            raise RegraDeNegocio(self.mensagem_conflito, code='conflito')

    def eventos_elegiveis(self, usuario):
        """Eventos dos próximos 60 dias, visíveis ao usuário, ainda sem registro dele."""
        agora = timezone.now()
        ja_registrados = self.do_usuario(usuario).filter(evento__isnull=False).values_list('evento_id', flat=True)
        return (
            Evento.objects.visiveis_para(usuario)
            .filter(data_inicio__gte=agora, data_inicio__lte=agora + self.JANELA_EVENTOS)
            .exclude(id__in=ja_registrados)
            .order_by('data_inicio')
        )

    def registrar_por_eventos(self, usuario, evento_ids):
        """Cria um período por evento informado (visível e ainda sem registro). Devolve quantos criou."""
        ja_registrados = set(
            self.do_usuario(usuario).filter(evento_id__in=evento_ids).values_list('evento_id', flat=True))
        eventos = Evento.objects.visiveis_para(usuario).filter(pk__in=evento_ids).exclude(pk__in=ja_registrados)
        criados = [
            self.modelo.objects.create(
                usuario=usuario, evento=evento, data_inicio=evento.data_inicio, data_fim=evento.data_fim)
            for evento in eventos
        ]
        return len(criados)
