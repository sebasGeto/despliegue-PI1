"""Puntos de integracion para notificaciones y eventos del modulo de citas.

Estas funciones son stubs que seran implementados por otras HUs del Sprint 2:
- HU12: Actualizacion automatica del calendario en tiempo real.
- HU16: Notificacion a secretaria ante reagendamiento.

Por ahora solo registran la accion; cuando las HUs correspondientes se
integren, reemplazaran el cuerpo de estas funciones.
"""

import logging

logger = logging.getLogger(__name__)


def notificar_cancelacion(cita):
    """Notifica la cancelacion de una cita al beneficiario y a secretaria.

    TODO: HU16 - integrar con servicio de notificaciones (correo / panel).
    TODO: HU12 - emitir evento de calendario en tiempo real.
    """
    logger.info(
        'Cancelacion de cita #%s por %s - motivo: %s',
        cita.pk,
        cita.cancelada_por,
        cita.motivo_cancelacion or '(sin motivo)',
    )

def emitir_evento_calendario(cita, tipo_evento):
    """Emite un evento de cambio en el calendario para actualizacion en tiempo real.

    Args:
        cita: instancia de Cita afectada.
        tipo_evento: str - 'creada', 'cancelada', 'reagendada', 'confirmada'.

    TODO: HU12 - integrar con WebSocket / SSE para refrescar el calendario
    de la secretaria sin recargar la pagina.
    """
    logger.info(
        'Evento calendario - cita #%s, tipo: %s',
        cita.pk,
        tipo_evento,
    )

def notificar_reagendamiento_secretaria(cita):
    """Notifica a la secretaria del consultorio sobre el reagendamiento de una cita.

    TODO: HU16 - integrar con servicio de notificaciones (correo / panel)
    para informar a la secretaria del cambio de horario, mostrando horario
    anterior y nuevo horario.
    """
    horario_anterior = cita.horario_anterior
    logger.info(
        'Reagendamiento de cita #%s por %s - de %s a %s',
        cita.pk,
        cita.reagendada_por,
        f'{horario_anterior.fecha} {horario_anterior.hora_inicio}' if horario_anterior else '(sin registro)',
        f'{cita.horario.fecha} {cita.horario.hora_inicio}',
    )