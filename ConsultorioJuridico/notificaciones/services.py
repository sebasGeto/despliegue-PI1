"""Servicios para la creación de notificaciones del sistema."""

from collections.abc import Iterable

from citas.models import Cita
from usuarios.models import Usuario

from .models import Notificacion


def crear_notificaciones_reagendamiento(
    cita: Cita,
    destinatarios: Iterable[Usuario],
) -> list[Notificacion]:
    """
    Crea notificaciones de tipo reagendamiento para una lista de usuarios.

    Parámetros:
        cita (Cita): Cita reagendada desde la cual se toma el caso y el horario.
        destinatarios (Iterable[Usuario]): Usuarios que recibirán la notificación.

    Retorno:
        list[Notificacion]: Lista de objetos Notificacion creados y persistidos
        mediante una sola operación bulk_create.
    """
    codigo_caso = cita.caso.codigo if cita.caso else "sin caso asignado"
    fecha = cita.horario.fecha.strftime("%d/%m/%Y")
    hora_inicio = cita.horario.hora_inicio.strftime("%H:%M")
    nombre_beneficiario = cita.beneficiario.nombre_completo

    mensaje = (
        f"Se reagendó la cita del beneficiario {nombre_beneficiario} "
        f"del caso {codigo_caso} para el {fecha} a las {hora_inicio}."
    )

    lista_de_notificaciones = [
        Notificacion(
            usuario=usuario,
            mensaje=mensaje,
            tipo=Notificacion.TIPO_REAGENDAMIENTO,
        )
        for usuario in destinatarios
    ]

    if not lista_de_notificaciones:
        return []

    Notificacion.objects.bulk_create(lista_de_notificaciones)
    return lista_de_notificaciones
