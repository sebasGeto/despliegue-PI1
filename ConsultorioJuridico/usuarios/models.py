from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    """Manager personalizado para Usuario sin campo username."""

    def create_user(self, documento, correo, nombre_completo, password=None, **extra_fields):
        if not documento:
            raise ValueError('El documento es obligatorio')
        if not correo:
            raise ValueError('El correo es obligatorio')
        correo = self.normalize_email(correo)
        user = self.model(
            documento=documento,
            correo=correo,
            nombre_completo=nombre_completo,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, documento, correo, nombre_completo, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(documento, correo, nombre_completo, password, **extra_fields)


class RolChoices(models.TextChoices):
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
        choices=RolChoices.choices,
        default=RolChoices.BENEFICIARIO,
    )
    acepta_tratamiento_datos = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "documento"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["correo", "nombre_completo"]

    def __str__(self):
        return f"{self.nombre_completo} - {self.documento}"


class Rol(models.Model):
    BENEFICIARIO = RolChoices.BENEFICIARIO
    ESTUDIANTE = RolChoices.ESTUDIANTE
    PROFESOR = RolChoices.PROFESOR
    ADMINISTRADOR = RolChoices.ADMINISTRADOR
    SECRETARIA = RolChoices.SECRETARIA

    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre


class Permiso(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    codigo = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'

    def __str__(self):
        return self.nombre


class UsuarioRol(models.Model):
    usuario = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='usuario_roles'
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.CASCADE,
        related_name='rol_usuarios'
    )

    class Meta:
        unique_together = ('usuario', 'rol')
        verbose_name = 'Usuario-Rol'
        verbose_name_plural = 'Usuarios-Roles'

    def __str__(self):
        return f'{self.usuario} → {self.rol}'


class RolPermiso(models.Model):
    rol = models.ForeignKey(
        Rol,
        on_delete=models.CASCADE,
        related_name='rol_permisos'
    )
    permiso = models.ForeignKey(
        Permiso,
        on_delete=models.CASCADE,
        related_name='permiso_roles'
    )

    class Meta:
        unique_together = ('rol', 'permiso')
        verbose_name = 'Rol-Permiso'
        verbose_name_plural = 'Roles-Permisos'

    def __str__(self):
        return f'{self.rol} → {self.permiso}'
