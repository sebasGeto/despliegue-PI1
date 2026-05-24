from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, Rol


class RegistroBeneficiarioForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = [
            "documento",
            "nombre_completo",
            "telefono",
            "correo",
            "direccion",
            "acepta_tratamiento_datos",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rol = Rol.BENEFICIARIO
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    documento = forms.CharField(max_length=20)
    password = forms.CharField(widget=forms.PasswordInput)