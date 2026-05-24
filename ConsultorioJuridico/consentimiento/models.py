from django.db import models
from django.conf import settings


class Autorizacion(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='autorizacion',
        verbose_name='Usuario',
    )
    acepta_tratamiento = models.BooleanField(
        default=False,
        verbose_name='Acepta tratamiento de datos',
    )
    fecha_autorizacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de autorización',
    )
    ip_registro = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='IP de registro',
    )

    class Meta:
        verbose_name = 'Autorización'
        verbose_name_plural = 'Autorizaciones'

    def __str__(self):
        return f'Autorización de {self.usuario}'
