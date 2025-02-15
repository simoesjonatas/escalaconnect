from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario
from django.core.exceptions import ValidationError


class SignupForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'})
    )
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
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2', 'telefone', 'aniversario', 'batismo', 'cpf']
    
    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        if first_name and last_name:
            cleaned_data['username'] = f"{first_name}.{last_name}".lower().replace(' ', '')
    
        username = f"{first_name}.{last_name}".lower().replace(' ', '')
        if Usuario.objects.filter(username=username).exists():
            self.add_error(None, f'O nome de usuário "{username}" já está em uso.')
            # raise ValidationError("Um usuário com este nome de usuário já existe.")

        return cleaned_data


    def clean_aceitar_termos(self):
        """Valida se o usuário aceitou os termos."""
        if not self.cleaned_data.get('aceitar_termos'):
            raise forms.ValidationError("Você deve aceitar os Termos de Uso para se cadastrar.")
        return self.cleaned_data['aceitar_termos']
    
    def save(self, commit=True):
        user = super(SignupForm, self).save(commit=False)
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        user.username = f"{first_name}.{last_name}".lower().replace(' ', '')
        if commit:
            user.save()
        return user
