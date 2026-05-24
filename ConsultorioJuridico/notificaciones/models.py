from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    TIPO_REAGENDAMIENTO = 'reagendamiento'

    TIPOS = [
        (TIPO_REAGENDAMIENTO, 'Reagendamiento'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        verbose_name='Usuario',
    )
    mensaje = models.TextField(verbose_name='Mensaje')
    tipo = models.CharField(
        max_length=50,
        choices=TIPOS,
        default=TIPO_REAGENDAMIENTO,
        verbose_name='Tipo',
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creacion',
    )
    leida = models.BooleanField(default=False, verbose_name='Leida')

    class Meta:
        verbose_name = 'Notificacion'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.usuario} - {self.tipo}'
