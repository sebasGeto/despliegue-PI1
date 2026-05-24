"""
Servicios para el envío automático de recordatorios de citas.
HU6 - Envío automático de recordatorios.
"""
from datetime import timedelta
try:
    import requests
except ImportError:
    requests = None

from django.utils import timezone
from django.conf import settings
from citas.models import Cita
from usuarios.emails import enviar_correo_recordatorio
from .models import LogRecordatorio

send_mail = enviar_correo_recordatorio


def procesar_recordatorios():
    """
    Evalúa todas las citas y envía recordatorios a las que corresponda.
    
    Lógica de los 4 escenarios de la HU6:
    - Solo citas con estado 'confirmada'
    - Solo citas cuya fecha esté dentro de las próximas 24 horas
    - NO procesa citas canceladas (ya filtrado por estado)
    - NO procesa citas cuya fecha ya pasó
    
    Para cada cita elegible: intenta enviar por email, con fallback a SMS.
    Registra cada intento en LogRecordatorio.
    
    Returns:
        int: Número de citas procesadas
    """
    # Obtener la fecha y hora actual
    ahora = timezone.now()
    limite = ahora + timedelta(hours=24)
    
    # Filtrar citas confirmadas cuya fecha esté dentro de las próximas 24 horas
    citas_confirmadas = Cita.objects.filter(estado='confirmada')
    
    citas_procesadas = 0
    
    for cita in citas_confirmadas:
        if _cita_es_elegible(cita, ahora, limite):
            _enviar_recordatorio(cita)
            citas_procesadas += 1
    
    return citas_procesadas


def _cita_es_elegible(cita, ahora, limite):
    """
    Valida que la cita sea elegible para recibir recordatorio.
    
    Criterios:
    - Estado debe ser 'confirmada'
    - La fecha de la cita debe estar dentro de las próximas 24 horas
    - La fecha de la cita no debe haber pasado
    
    Args:
        cita: Instancia del modelo Cita
        ahora: Fecha y hora actual
        limite: Fecha y hora límite (ahora + 24 horas)
    
    Returns:
        bool: True si la cita es elegible, False en caso contrario
    """
    # Verificar que el estado sea confirmado
    if cita.estado != 'confirmada':
        return False
    
    # Obtener la fecha y hora de la cita
    fecha_cita = cita.horario.fecha
    hora_cita = cita.horario.hora_inicio
    
    # Combinar fecha y hora en un datetime
    from datetime import datetime, time as time_module
    if isinstance(hora_cita, time_module):
        fecha_hora_cita = datetime.combine(fecha_cita, hora_cita)
        fecha_hora_cita = timezone.make_aware(fecha_hora_cita)
    else:
        # Si ya es un datetime
        fecha_hora_cita = timezone.make_aware(fecha_cita) if fecha_cita.tzinfo is None else fecha_cita
    
    # Verificar que la cita no haya pasado
    if fecha_hora_cita < ahora:
        return False
    
    # Verificar que la cita esté dentro de las próximas 24 horas
    if fecha_hora_cita > limite:
        return False
    
    return True


def _enviar_recordatorio(cita):
    """
    Intenta enviar un recordatorio para la cita dada.
    Primero intenta enviar por email, si falla usa SMS como fallback.
    
    Args:
        cita: Instancia del modelo Cita
    """
    correo = cita.beneficiario.correo
    telefono = cita.beneficiario.telefono

    if correo:
        try:
            email_exitoso, error_email = _enviar_email(cita)
        except Exception as exc:
            email_exitoso, error_email = False, str(exc)
        if email_exitoso:
            return True

        if telefono:
            try:
                sms_exitoso, _ = _enviar_sms(cita)
            except Exception as exc:
                _guardar_log(cita, 'sms', False, str(exc))
                return False
            return sms_exitoso

        _guardar_log(cita, 'email', False, error_email or 'Error enviando correo y sin teléfono para fallback')
        return False

    if telefono:
        try:
            sms_exitoso, _ = _enviar_sms(cita)
        except Exception as exc:
            _guardar_log(cita, 'sms', False, str(exc))
            return False
        return sms_exitoso

    _guardar_log(cita, 'sms', False, 'Sin correo ni teléfono registrado para el beneficiario')
    return False


def _enviar_email(cita, registrar_log=True):
    """
    Envía recordatorio por email al beneficiario de la cita.
    
    Args:
        cita: Instancia del modelo Cita
    
    Returns:
        tuple[bool, str]: Estado de envío y mensaje de error (si aplica)
    """
    beneficiario = cita.beneficiario
    correo = beneficiario.correo

    if not correo:
        return False, 'El beneficiario no tiene correo registrado'

    fecha_cita = cita.horario.fecha.strftime('%d/%m/%Y')
    hora_cita = cita.horario.hora_inicio.strftime('%H:%M')
    contexto = {
        'nombre_beneficiario': beneficiario.nombre_completo,
        'fecha_cita': fecha_cita,
        'hora_cita': hora_cita,
        'tipo_atencion': cita.get_tipo_atencion_display(),
    }

    try:
        enviar_correo_recordatorio(cita)
        if registrar_log:
            _guardar_log(cita, 'email', True)
        return True, ''
    except Exception as exc:
        return False, str(exc)


def _enviar_sms(cita, registrar_log=True):
    """
    Envía recordatorio por SMS al beneficiario de la cita usando API REST.
    
    Args:
        cita: Instancia del modelo Cita
    
    Returns:
        tuple[bool, str]: Estado de envío y mensaje de error (si aplica)
    """
    if not getattr(settings, 'SMS_HABILITADO', False):
        error = 'SMS no configurado'
        if registrar_log:
            _guardar_log(cita, 'sms', False, error)
        return False, error

    beneficiario = cita.beneficiario
    telefono = beneficiario.telefono

    if not telefono:
        error = 'El beneficiario no tiene teléfono registrado'
        if registrar_log:
            _guardar_log(cita, 'sms', False, error)
        return False, error

    sms_api_url = getattr(settings, 'SMS_API_URL', '')
    sms_api_key = getattr(settings, 'SMS_API_KEY', '')
    sms_timeout = int(getattr(settings, 'SMS_TIMEOUT', 10))

    if not sms_api_url:
        error = 'SMS no configurado: falta SMS_API_URL'
        if registrar_log:
            _guardar_log(cita, 'sms', False, error)
        return False, error

    if requests is None:
        error = 'SMS no disponible: falta la dependencia requests'
        if registrar_log:
            _guardar_log(cita, 'sms', False, error)
        return False, error

    payload = {
        'to': telefono,
        'message': (
            f"Recordatorio Consultorio Juridico Icesi: cita el "
            f"{cita.horario.fecha.strftime('%d/%m/%Y')} a las {cita.horario.hora_inicio.strftime('%H:%M')}."
        ),
    }
    headers = {'Content-Type': 'application/json'}
    if sms_api_key:
        headers['Authorization'] = f'Bearer {sms_api_key}'

    try:
        response = requests.post(
            sms_api_url,
            json=payload,
            headers=headers,
            timeout=sms_timeout,
        )
        response.raise_for_status()
        if registrar_log:
            _guardar_log(cita, 'sms', True)
        return True, ''
    except requests.RequestException as exc:
        error = str(exc)
        if registrar_log:
            _guardar_log(cita, 'sms', False, error)
        return False, error


def reintentar_fallidos():
    """
    Reintenta logs fallidos sobre citas aún elegibles.
    Máximo 3 intentos por cita/log.
    """
    ahora = timezone.now()
    limite = ahora + timedelta(hours=24)
    logs_fallidos = (
        LogRecordatorio.objects
        .select_related('cita__horario', 'cita__beneficiario')
        .filter(estado='fallido', intentos__lt=3, cita__estado='confirmada')
        .order_by('fecha_intento')
    )

    for log in logs_fallidos:
        cita = log.cita
        if not _cita_es_elegible(cita, ahora, limite):
            continue

        if cita.beneficiario.correo:
            exito, error = _enviar_email(cita, registrar_log=False)
            if not exito and cita.beneficiario.telefono:
                exito, error = _enviar_sms(cita, registrar_log=False)
            elif not exito and not cita.beneficiario.telefono:
                error = error or 'Sin correo ni teléfono registrado para el beneficiario'
        elif cita.beneficiario.telefono:
            exito, error = _enviar_sms(cita, registrar_log=False)
        else:
            exito, error = False, 'Sin correo ni teléfono registrado para el beneficiario'

        log.intentos += 1
        log.fecha_envio = timezone.now() if exito else None
        log.estado = 'enviado' if exito else 'fallido'
        log.mensaje_error = '' if exito else error
        log.save(update_fields=['intentos', 'fecha_envio', 'estado', 'mensaje_error'])


def _guardar_log(cita, canal, exito, error=''):
    """
    Guarda un registro del intento de envío de recordatorio.
    
    Args:
        cita: Instancia del modelo Cita
        canal: 'email' o 'sms'
        exito: True si el envío fue exitoso, False si falló
        error: Mensaje de error si el envío falló
    
    Returns:
        LogRecordatorio: Instancia del log creado
    """
    from django.utils import timezone
    
    estado = 'enviado' if exito else 'fallido'
    fecha_envio = timezone.now() if exito else None
    
    return LogRecordatorio.objects.create(
        cita=cita,
        canal=canal,
        estado=estado,
        fecha_envio=fecha_envio,
        mensaje_error=error,
    )