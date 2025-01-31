from django.db import models
from django.utils.timezone import now
from escala.models import Funcao

class Planejamento(models.Model):
    nome = models.CharField(max_length=255)
    data_cadastro = models.DateTimeField(default=now)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

class PlanejamentoFuncao(models.Model):
    planejamento = models.ForeignKey(Planejamento, on_delete=models.CASCADE, related_name="funcoes")
    funcao = models.ForeignKey(Funcao, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.planejamento.nome} - {self.funcao.nome}"
