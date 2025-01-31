from django import forms
from .models import Planejamento, PlanejamentoFuncao
from escala.models import Funcao

class PlanejamentoForm(forms.ModelForm):
    class Meta:
        model = Planejamento
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PlanejamentoFuncaoForm(forms.ModelForm):
    class Meta:
        model = PlanejamentoFuncao
        fields = ['funcao']

    def __init__(self, *args, **kwargs):
        planejamento = kwargs.pop('planejamento', None)
        super(PlanejamentoFuncaoForm, self).__init__(*args, **kwargs)

        if planejamento:
            self.fields['funcao'].queryset = Funcao.objects.filter(equipe__isnull=False)