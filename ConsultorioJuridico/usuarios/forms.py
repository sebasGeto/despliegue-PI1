from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario


class LoginForm(forms.Form):
    """Formulario de inicio de sesión por documento."""
    documento = forms.CharField(
        max_length=20,
        label="Usuario",
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Contraseña",
    )


class RegistroPaso1Form(forms.ModelForm):
    """Paso 1 del registro: datos personales."""
    class Meta:
        model = Usuario
        fields = ["documento", "nombre_completo", "telefono", "correo", "direccion"]
        labels = {
            "documento": "Documento de identidad",
            "nombre_completo": "Nombre Completo",
            "telefono": "Teléfono",
            "correo": "Correo",
            "direccion": "Dirección",
        }


class RegistroPaso2Form(forms.Form):
    """Paso 2 del registro: contraseña y consentimiento."""
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="Cree una contraseña",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Repita la contraseña",
    )
    acepta_tratamiento_datos = forms.BooleanField(
        required=True,
        label="Autorizo el tratamiento de datos personales bajo la Ley 1581 de 2012",
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data