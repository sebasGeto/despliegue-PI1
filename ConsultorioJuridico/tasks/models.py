from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.TextChoices):
    BENEFICIARIO = "beneficiario", "Beneficiario"
    ESTUDIANTE = "estudiante", "Estudiante"
    PROFESOR = "profesor", "Profesor"
    ADMINISTRADOR = "administrador", "Administrador"
    SECRETARIA = "secretaria", "Secretaria"


class Usuario(AbstractUser):
    username = None
    email = None
    first_name = None
    last_name = None

    documento = models.CharField(max_length=20, unique=True)
    nombre_completo = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.BENEFICIARIO,
    )
    acepta_tratamiento_datos = models.BooleanField(default=False)

    USERNAME_FIELD = "documento"
    REQUIRED_FIELDS = ["correo", "nombre_completo"]

    def __str__(self):
        return f"{self.nombre_completo} - {self.documento}"


class PerfilBeneficiario(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="perfil_beneficiario"
    )
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    barrio = models.CharField(max_length=100, blank=True, null=True)
    estrato = models.PositiveSmallIntegerField(blank=True, null=True)
    nacionalidad = models.CharField(max_length=100, blank=True, null=True)
    genero = models.CharField(max_length=50, blank=True, null=True)
    discapacidad = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario.nombre_completo}"