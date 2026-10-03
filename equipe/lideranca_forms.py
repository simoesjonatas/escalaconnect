from django import forms
from .models import Lideranca
from equipe.models import Equipe
from usuario.models import Usuario

class LiderancaForm(forms.ModelForm):
    class Meta:
        model = Lideranca
        fields = ['usuario', 'equipe']
        widgets = {
            # data-busca: vira campo de busca com lista (static/js/busca-select.js)
            'usuario': forms.Select(attrs={'class': 'form-control', 'data-busca': '', 'data-busca-placeholder': 'Digite o nome para buscar…'}),
            'equipe': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        equipe = kwargs.pop('equipe', None)
        super(LiderancaForm, self).__init__(*args, **kwargs)

        usuario = self.fields['usuario']
        usuario.queryset = usuario.queryset.filter(is_active=True).order_by('first_name', 'last_name', 'username')
        usuario.label_from_instance = lambda u: u.get_full_name() or u.username

        if equipe:
            self.fields['equipe'].queryset = Equipe.objects.filter(pk=equipe.pk)
            self.fields['equipe'].initial = equipe

        # Se for um update, desabilitar o campo e remover do formulário enviado
        if self.instance.pk:
            self.fields['equipe'].widget.attrs['readonly'] = True
            self.fields['equipe'].queryset = Equipe.objects.filter(pk=self.instance.equipe.pk)

            # self.fields['equipe'].widget.attrs['disabled'] = True  # Bloqueia no HTML
    
    def clean_equipe(self):
        """ Mantém a equipe original no update """
        if self.instance.pk:
            return self.instance.equipe
        return self.cleaned_data.get('equipe')
    
    def clean(self):
        cleaned_data = super().clean()
        usuario = cleaned_data.get("usuario")
        equipe = cleaned_data.get("equipe")

        if Lideranca.objects.filter(usuario=usuario, equipe=equipe).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este usuário já é um líder desta equipe.")

        return cleaned_data
