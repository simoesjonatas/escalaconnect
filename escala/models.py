from django.db import models
from django.conf import settings
from evento.models import Evento


class Funcao(models.Model):
    nome = models.CharField(max_length=255)
    equipe = models.ForeignKey('equipe.Equipe', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'Função'
        verbose_name_plural = 'Funções'

    def __str__(self):
        return self.nome

class EscalaFixa(models.Model):
    """Escala que se repete todo mês numa equipe (ex.: "1º domingo de manhã: Fulano no Som").

    Desligada (ou inexistente), a equipe é flexível: o líder escala culto a culto.
    As regras ficam em escala/fixa.py.
    """
    equipe = models.OneToOneField('equipe.Equipe', on_delete=models.CASCADE, related_name='escala_fixa')
    ativa = models.BooleanField(default=False)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Escala fixa'
        verbose_name_plural = 'Escalas fixas'

    def __str__(self):
        return f"Escala fixa: {self.equipe} ({'ativa' if self.ativa else 'desligada'})"


class EscalaFixaItem(models.Model):
    """Uma linha da escala fixa: em qual culto (dia + turno + semana do mês), quem serve e em qual função."""
    TURNO_MANHA, TURNO_TARDE, TURNO_NOITE = 'manha', 'tarde', 'noite'
    TURNOS = [(TURNO_MANHA, 'Manhã'), (TURNO_TARDE, 'Tarde'), (TURNO_NOITE, 'Noite')]
    # Mesmo número de date.weekday().
    DIAS = [(0, 'Segunda'), (1, 'Terça'), (2, 'Quarta'), (3, 'Quinta'), (4, 'Sexta'), (5, 'Sábado'), (6, 'Domingo')]
    TODA_SEMANA = 0
    SEMANAS = [(0, 'Toda semana'), (1, '1º'), (2, '2º'), (3, '3º'), (4, '4º'), (5, '5º')]

    escala_fixa = models.ForeignKey(EscalaFixa, on_delete=models.CASCADE, related_name='itens')
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS)
    turno = models.CharField(max_length=5, choices=TURNOS)
    semana = models.PositiveSmallIntegerField(choices=SEMANAS, default=TODA_SEMANA)
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ['dia_semana', 'turno', 'semana', 'funcao__nome', 'pk']

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.get_turno_display()} ({self.get_semana_display()}): {self.funcao} – {self.usuario}"


class Escala(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    confirmada = models.BooleanField(default=False)
    data_confirmacao = models.DateTimeField(null=True, blank=True)
    # Linha da escala fixa que gerou esta escala: impede preencher de novo o mesmo culto
    # (troca manual do líder e impedimento aprovado continuam valendo).
    item_fixo = models.ForeignKey(EscalaFixaItem, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='escalas')
    # Preenchida pela escala fixa e ainda sem o aviso de resumo (um push por pessoa, não por culto).
    aviso_pendente = models.BooleanField(default=False)

    @property
    def equipe(self):
        return self.funcao.equipe if self.funcao else None
    
    @property
    def data_inicio(self):
        return self.evento.data_inicio if self.evento.data_inicio else None
    
    def __str__(self):
        return self.evento.nome
    
    def has_impedimento(self):
        """ Verifica se há desistências não aprovadas para esta escala. """
        return Desistencia.objects.filter(escala=self, aprovada=False).exists()
    
    def has_solicitacao_troca_aberta(self):
        """ Verifica se há solicitações de troca não aprovadas para esta escala. """
        return SolicitacaoTroca.objects.filter(escala_origem=self, aprovada=False).exists()
    
    def get_pending_troca_id(self):
        """ Retorna o ID da solicitação de troca aberta, se existir. """
        troca = SolicitacaoTroca.objects.filter(escala_origem=self, aprovada=False).first()
        return troca.id if troca else None
    
    def clear_escala(self):
        """ Limpa a escala removendo a confirmação, a data de confirmação e o usuário associado. """
        self.data_confirmacao = None
        self.confirmada = False
        self.usuario = None
        self.save()



class SolicitacaoTroca(models.Model):
    escala_origem = models.ForeignKey(Escala, related_name='solicitacoes_origem', on_delete=models.CASCADE)
    escala_destino = models.ForeignKey(Escala, related_name='solicitacoes_destino', on_delete=models.SET_NULL, null=True)
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='solicitacoes_feitas', on_delete=models.CASCADE)
    lider_aprovador = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='solicitacoes_aprovadas', on_delete=models.CASCADE, null=True)
    tipo_solicitacao = models.CharField(max_length=255)  # 'troca', 'desistencia', 'rendimento'
    aprovada = models.BooleanField(default=False)
    data_solicitacao = models.DateTimeField()
    data_aprovacao = models.DateTimeField(null=True,blank=True)
    
    def __str__(self):
        return f"Solicitação: {self.tipo_solicitacao} - Origem: {self.escala_origem} - Destino: {self.escala_destino}"


class Desistencia(models.Model):
    escala = models.ForeignKey('Escala', on_delete=models.CASCADE)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    motivo = models.TextField(verbose_name="Motivo da Desistência")
    aprovada = models.BooleanField(default=False)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Desistência: {self.usuario} - Escala: {self.escala}"


class Rendimento(models.Model):
    """Voluntário que se ofereceu para ocupar uma vaga em aberto; o líder aprova ou recusa."""
    escala = models.ForeignKey(Escala, on_delete=models.CASCADE)
    candidato = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    aprovada = models.BooleanField(default=False)
    data_candidatura = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Rendimento: {self.candidato} - Escala: {self.escala}"

