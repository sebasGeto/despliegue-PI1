from django.db import models
from django.conf import settings


class LogRecordatorio(models.Model):
    """
    Log de intentos de envío de recordatorios de citas.
    Registra cada intento de notificación (email o SMS) con su estado.
    """
    CANAL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
    ]

    cita = models.ForeignKey(
        'citas.Cita',
        on_delete=models.CASCADE,
        related_name='recordatorios',
        verbose_name='Cita',
    )
    canal = models.CharField(
        max_length=10,
        choices=CANAL_CHOICES,
        verbose_name='Canal de envío',
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado del envío',
    )
    fecha_intento = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del intento',
    )
    fecha_envio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de envío',
    )
    mensaje_error = models.TextField(
        blank=True,
        default='',
        verbose_name='Mensaje de error',
    )
    intentos = models.IntegerField(
        default=1,
        verbose_name='Número de intentos',
    )

    class Meta:
        ordering = ['-fecha_intento']
        verbose_name = 'Log de Recordatorio'
        verbose_name_plural = 'Logs de Recordatorios'

    def __str__(self):
        return f'Recordatorio {self.cita.id} - {self.get_canal_display()} [{self.get_estado_display()}]'
