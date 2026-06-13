from django import forms
from django.contrib.auth import get_user_model
from .utils import validate_cpf, normalizar_telefone, validate_telefone

User = get_user_model()

TELEFONE_WIDGET_ATTRS = {
    'class': 'form-control',
    'type': 'tel',
    'inputmode': 'tel',
    'placeholder': '(21) 99999-9999',
}

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'telefone', 'aniversario', 'cpf','batismo']
        widgets = {
            'aniversario': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'batismo': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'telefone': forms.TextInput(attrs=TELEFONE_WIDGET_ATTRS),
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

    def clean_telefone(self):
        telefone = normalizar_telefone(self.cleaned_data.get('telefone'))
        if telefone:
            validate_telefone(telefone)
        return telefone

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if commit:
            usuario.save()
        return usuario


class PerfilContatoForm(forms.ModelForm):
    """Atualização de contato (email/telefone) feita pelo próprio usuário no perfil."""

    class Meta:
        model = User
        fields = ['email', 'telefone']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs=TELEFONE_WIDGET_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este email já está em uso.")
        return email

    def clean_telefone(self):
        telefone = normalizar_telefone(self.cleaned_data.get('telefone'))
        if telefone:
            validate_telefone(telefone)
        return telefone


class RecuperarSenhaForm(forms.Form):
    cpf = forms.CharField(max_length=14, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CPF'}))
    data_nascimento = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))