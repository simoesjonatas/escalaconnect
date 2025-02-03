from django import forms
from django.contrib.auth import get_user_model
from .utils import validate_cpf

User = get_user_model()

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'telefone', 'aniversario', 'cpf']
        widgets = {
            'aniversario': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    # def clean_cpf(self):
    #     cpf = self.cleaned_data['cpf']
    #     if not validate_cpf(cpf):
    #         raise forms.ValidationError("Por favor, insira um CPF válido.")
    #     return cpf

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este email já está em uso.")
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if commit:
            usuario.save()
        return usuario
