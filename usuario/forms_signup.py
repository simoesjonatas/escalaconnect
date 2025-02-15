from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario

class SignupForm(UserCreationForm):
    telefone = forms.CharField(
        max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    aniversario = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    batismo = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    cpf = forms.CharField(
        max_length=11, required=True, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True, widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    aceitar_termos = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Aceito os Termos de Uso"
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password1', 'password2', 'telefone', 'aniversario', 'batismo', 'cpf']

    def clean_aceitar_termos(self):
        """Valida se o usuário aceitou os termos."""
        if not self.cleaned_data.get('aceitar_termos'):
            raise forms.ValidationError("Você deve aceitar os Termos de Uso para se cadastrar.")
        return self.cleaned_data['aceitar_termos']
