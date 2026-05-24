from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def _enviar_correo(subject, message, recipient_list, html_message=None):
    """Envía un correo utilizando la configuración de Django."""
    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        html_message=html_message,
        fail_silently=False,
    )


def enviar_correo_bienvenida(usuario):
    """Envía un correo de bienvenida cuando un usuario completa su registro."""
    asunto = "Bienvenido al Consultorio Jurídico ICESI"
    mensaje = (
        f"Hola {usuario.nombre_completo},\n\n"
        "Tu registro en el Consultorio Jurídico ICESI fue exitoso.\n"
        f"Documento: {usuario.documento}\n"
        f"Correo registrado: {usuario.correo}\n\n"
        "Ya puedes iniciar sesión con tu documento y la contraseña que registraste.\n\n"
        "Este es un mensaje automático, por favor no responder."
    )

    return _enviar_correo(
        asunto,
        mensaje,
        [usuario.correo],
    )


def enviar_correo_recordatorio(cita):
    """Envía un correo recordatorio para una cita pendiente o confirmada."""
    beneficiario = cita.beneficiario
    asunto = "Recordatorio de cita - Consultorio Jurídico Icesi"
    fecha_cita = cita.horario.fecha.strftime('%d/%m/%Y')
    hora_cita = cita.horario.hora_inicio.strftime('%H:%M')
    contexto = {
        'nombre_beneficiario': beneficiario.nombre_completo,
        'fecha_cita': fecha_cita,
        'hora_cita': hora_cita,
        'tipo_atencion': cita.get_tipo_atencion_display(),
    }
    mensaje = (
        f"Hola {beneficiario.nombre_completo},\n\n"
        f"Le recordamos su cita programada para el {fecha_cita} a las {hora_cita} ({contexto['tipo_atencion']}).\n\n"
        "Por favor, recuerde asistir en el horario indicado. Si necesita cancelar o reagendar, contáctenos con anticipación.\n\n"
        "Este es un mensaje automático, por favor no responder."
    )
    html_message = render_to_string('recordatorios/recordatorio_email.html', contexto)

    return _enviar_correo(
        asunto,
        mensaje,
        [beneficiario.correo],
        html_message=html_message,
    )
