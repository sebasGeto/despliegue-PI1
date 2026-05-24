from django.db.models.signals import post_save
from django.dispatch import receiver
from citas.models import Cita
from .services import generar_metricas_asistencia


@receiver(post_save, sender=Cita)
def _on_cita_saved_recalcular_metricas(sender, instance: Cita, created, **kwargs):
    """Recalcula métricas cuando una cita cambia a estado finalizado.

    Se considera finalizada si el estado es 'cumplida' o 'no_asistio'.
    """
    if instance.estado in ('cumplida', 'no_asistio'):
        try:
            generar_metricas_asistencia()
        except Exception:
            # No levantar errores desde la señal
            pass
