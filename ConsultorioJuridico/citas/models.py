from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime


class Caso(models.Model):
    """Modelo simplificado de Caso jurídico (puente hasta integración con módulo de Casos)."""
    SALA_CHOICES = [
        ('civil', 'Civil'),
        ('laboral', 'Laboral'),
        ('penal', 'Penal'),
        ('publico', 'Público'),
        ('familia', 'Familia'),
    ]

    ESTADO_CASO_CHOICES = [
        ('en_estudio', 'En estudio'),
        ('asignado', 'Asignado'),
        ('cerrado', 'Cerrado'),
        ('rechazado', 'Rechazado'),
    ]

    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código del caso',
    )
    beneficiario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='casos',
        verbose_name='Beneficiario',
    )
    sala_juridica = models.CharField(
        max_length=20,
        choices=SALA_CHOICES,
        verbose_name='Sala jurídica',
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CASO_CHOICES,
        default='en_estudio',
        verbose_name='Estado del caso',
    )
    estudiante_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='casos_asignados',
        verbose_name='Estudiante asignado',
        limit_choices_to={'rol': 'estudiante'},
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )

    class Meta:
        verbose_name = 'Caso'
        verbose_name_plural = 'Casos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.codigo} - {self.get_sala_juridica_display()} [{self.get_estado_display()}]'
class HorarioDisponible(models.Model):
    """Horarios disponibles para agendar citas en el consultorio."""
    fecha = models.DateField(verbose_name='Fecha')
    hora_inicio = models.TimeField(verbose_name='Hora de inicio')
    hora_fin = models.TimeField(verbose_name='Hora de fin')
    disponible = models.BooleanField(
        default=True,
        verbose_name='Disponible',
    )

    class Meta:
        verbose_name = 'Horario disponible'
        verbose_name_plural = 'Horarios disponibles'
        ordering = ['fecha', 'hora_inicio']
        unique_together = ['fecha', 'hora_inicio']

    def __str__(self):
        estado = 'Disponible' if self.disponible else 'Ocupado'
        return f'{self.fecha} {self.hora_inicio} - {self.hora_fin} ({estado})'
    
class Cita(models.Model):
    """Cita agendada en el consultorio jurídico."""

    TIPO_ATENCION = [
        ('presencial', 'Presencial'),
        ('telefonica', 'Telefónica'),
        ('virtual', 'Virtual'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de confirmación'),
        ('confirmada', 'Confirmada'),
        ('cumplida', 'Cumplida'),
        ('no_asistio', 'No asistió'),
        ('cancelada', 'Cancelada'),
    ]

    TRANSICIONES_VALIDAS = {
        'pendiente': ['confirmada', 'cancelada'],
        'confirmada': ['cumplida', 'no_asistio', 'cancelada'],
        'cumplida': [],
        'no_asistio': [],
        'cancelada': [],
    }

    beneficiario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name='Beneficiario',
    )
    caso = models.ForeignKey(
        Caso,
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name='Caso',
        null=True,
        blank=True,
    )
    horario = models.ForeignKey(
        HorarioDisponible,
        on_delete=models.PROTECT,
        related_name='citas',
        verbose_name='Horario',
    )
    tipo_atencion = models.CharField(
        max_length=15,
        choices=TIPO_ATENCION,
        verbose_name='Tipo de atención',
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado',
    )
    motivo = models.TextField(
        blank=True,
        verbose_name='Motivo de la consulta',
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación',
    )
    fecha_confirmacion = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Fecha de confirmación',
    )
    fecha_cancelacion = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Fecha de cancelación',
    )

    motivo_cancelacion = models.TextField(
        blank=True,
        default='',
        verbose_name='Motivo de cancelación',
    )
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_canceladas',
        verbose_name='Cancelada por',
    )

    horario_anterior = models.ForeignKey(
        'HorarioDisponible',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_reagendadas_desde',
        verbose_name='Horario anterior',
    )
    fecha_reagendamiento = models.DateTimeField(
        blank=True, null=True,
        verbose_name='Fecha de reagendamiento',
    )
    reagendada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_reagendadas',
        verbose_name='Reagendada por',
    )
    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'Cita #{self.pk} - {self.beneficiario} [{self.get_estado_display()}]'

    def cambiar_estado(self, nuevo_estado, usuario=None, motivo=''):
        """Cambia el estado validando las transiciones permitidas.

        Args:
            nuevo_estado: estado destino (clave de ESTADO_CHOICES).
            usuario: opcional, usuario que ejecuta la acción. Se registra
                     en cancelada_por cuando el nuevo_estado es 'cancelada'.
            motivo: opcional, texto libre con el motivo. Se registra en
                    motivo_cancelacion cuando el nuevo_estado es 'cancelada'.
        """
        estados_permitidos = self.TRANSICIONES_VALIDAS.get(self.estado, [])
        if nuevo_estado not in estados_permitidos:
            raise ValidationError(
                f'No se puede cambiar de "{self.get_estado_display()}" '
                f'a "{dict(self.ESTADO_CHOICES).get(nuevo_estado)}".'
            )
        if nuevo_estado == 'cancelada' and self.es_pasada():
            raise ValidationError(
                'No se puede cancelar una cita cuya fecha y hora ya pasaron.'
            )
        self.estado = nuevo_estado
        if nuevo_estado == 'confirmada':
            self.fecha_confirmacion = timezone.now()
        elif nuevo_estado == 'cancelada':
            self.fecha_cancelacion = timezone.now()
            self.motivo_cancelacion = motivo
            self.cancelada_por = usuario
            self.horario.disponible = True
            self.horario.save()
        self.save()

    def puede_confirmar(self):
        """Verifica si la cita puede ser confirmada."""
        return self.estado == 'pendiente'

    def es_pasada(self):
        """Verifica si la cita ya ocurrió (fecha + hora de inicio < ahora)."""
        inicio_cita = timezone.make_aware(
            datetime.datetime.combine(self.horario.fecha, self.horario.hora_inicio)
        )
        return inicio_cita < timezone.now()

    def puede_cancelar(self):
        """Verifica si la cita puede ser cancelada."""
        return self.estado in ['pendiente', 'confirmada'] and not self.es_pasada()
    
    def puede_reagendar(self):
        """Verifica si la cita puede ser reagendada."""
        return self.estado in ['pendiente', 'confirmada'] and not self.es_pasada()

    def get_inicio_datetime(self):
        """Retorna el datetime de inicio de la cita (timezone-aware)."""
        return timezone.make_aware(
            datetime.datetime.combine(self.horario.fecha, self.horario.hora_inicio)
        )

    def esta_pendiente_sin_confirmacion(self):
        """Indica si la cita sigue pendiente y no fue confirmada."""
        return self.estado == 'pendiente'

    def esta_vencida_sin_confirmacion(self, tolerancia_minutos: int = 15) -> bool:

        """True si una cita pendiente ya venció (o está por vencer) sin confirmación.

        La tolerancia se usa para que no sea estrictamente al minuto exacto.
        """
        if not self.esta_pendiente_sin_confirmacion():
            return False

        inicio = self.get_inicio_datetime()
        limite = inicio - datetime.timedelta(minutes=tolerancia_minutos)
        return limite <= timezone.now()

    def requiere_atencion_automatico(self, tolerancia_minutos: int = 15) -> bool:
        """Alias reutilizable para la HU14 (detección visual, sin cambios en BD).

        Ojo: en plantillas Django NO se debe llamar con parámetros.
        Para eso existe `requiere_atencion_automatico_15`.
        """
        return self.esta_vencida_sin_confirmacion(tolerancia_minutos=tolerancia_minutos)


    @property
    def requiere_atencion_automatico_15(self) -> bool:
        """Conveniencia para HU14 en templates (tolerancia fija 15 min)."""
        return self.requiere_atencion_automatico(tolerancia_minutos=15)
    @property
    def ultimo_recordatorio(self):
        """Devuelve el último intento de recordatorio asociado a la cita."""
        return self.recordatorios.order_by('-fecha_intento').first()


class RegistroAsistencia(models.Model):
    """Registro de asistencia o inasistencia a una cita (HU3)."""
    cita = models.OneToOneField(
        Cita,
        on_delete=models.CASCADE,
        related_name='asistencia',
        verbose_name='Cita',
    )
    asistio = models.BooleanField(verbose_name='¿Asistió?')
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro',
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='asistencias_registradas',
        verbose_name='Registrado por',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
    )

    class Meta:
        verbose_name = 'Registro de asistencia'
        verbose_name_plural = 'Registros de asistencia'
        ordering = ['-fecha_registro']

    def __str__(self):
        estado = 'Asistió' if self.asistio else 'No asistió'
        return f'{self.cita} - {estado}'