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

class Escala(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    confirmada = models.BooleanField(default=False)
    data_confirmacao = models.DateTimeField(null=True, blank=True)
    
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
    escala = models.ForeignKey(Escala, on_delete=models.CASCADE)
    candidato = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    aprovada = models.BooleanField()
    data_candidatura = models.DateTimeField()
    data_aprovacao = models.DateTimeField()
    
    def __str__(self):
        return f"Rendimento: {self.candidato} - Escala: {self.escala}"

