import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from usuarios.models import Usuario, RolChoices
from usuarios.emails import enviar_correo_recordatorio
from notificaciones.models import Notificacion
from notificaciones.services import crear_notificaciones_reagendamiento
from .models import Cita, Caso, HorarioDisponible
from .notificaciones import notificar_cancelacion, emitir_evento_calendario, notificar_reagendamiento_secretaria


logger = logging.getLogger(__name__)


def get_citas_queryset_for_user(user):
    """Devuelve el queryset de citas permitidas para el rol del usuario."""
    if user.rol == 'beneficiario':
        return Cita.objects.filter(beneficiario=user)
    if user.rol == 'estudiante':
        return Cita.objects.filter(caso__estudiante_asignado=user)
    if user.rol in ['administrador', 'secretaria']:
        return Cita.objects.all()
    if user.rol == 'profesor':
        return Cita.objects.none()
    return Cita.objects.none()


def get_casos_queryset_for_user(user):
    """Devuelve el queryset de casos permitidos para el rol del usuario."""
    if user.rol == 'beneficiario':
        return Caso.objects.filter(beneficiario=user)
    if user.rol == 'estudiante':
        return Caso.objects.filter(estudiante_asignado=user)
    if user.rol in ['administrador', 'secretaria']:
        return Caso.objects.all()
    if user.rol == 'profesor':
        return Caso.objects.none()
    return Caso.objects.none()


def serialize_cita(cita, user_role):

    if cita is None:
        return None

    fecha = cita.horario.fecha.strftime('%d/%m/%Y')
    hora = cita.horario.hora_inicio.strftime('%H:%M')

    data = {
        'id': cita.pk,
        'caso_codigo': cita.caso.codigo if cita.caso else None,
        'fecha': fecha,
        'hora': hora,
        'fecha_hora': f'{fecha} {hora}',
        'tipo_atencion': cita.get_tipo_atencion_display(),
        'estado': cita.estado,
        'estado_display': cita.get_estado_display(),
        # HU14: detección visual de citas pendientes que ya requieren atención (sin cambios en BD).
        'requiere_atencion': cita.requiere_atencion_automatico(tolerancia_minutos=15) if cita.estado == 'pendiente' else False,
        'sala_juridica': cita.caso.get_sala_juridica_display() if cita.caso else None,
        'estudiante_asignado': cita.caso.estudiante_asignado.nombre_completo if cita.caso and cita.caso.estudiante_asignado else None,
        'beneficiario_id': cita.beneficiario.pk,
        'estudiante_asignado_id': cita.caso.estudiante_asignado.pk if cita.caso and cita.caso.estudiante_asignado else None,
    }

    if user_role in ['administrador', 'secretaria']:
        data['beneficiario'] = cita.beneficiario.nombre_completo
        data['beneficiario_id'] = cita.beneficiario.pk
    return data


def serialize_notificacion(notificacion):
    return {
        'id': notificacion.pk,
        'mensaje': notificacion.mensaje,
        'fecha_creacion': timezone.localtime(notificacion.fecha_creacion).strftime('%d/%m/%Y %H:%M'),
    }


@login_required
def home_view(request):
    """Vista del dashboard principal."""
    hoy = timezone.localdate()
    ahora = timezone.localtime().time()

    citas = get_citas_queryset_for_user(request.user).select_related('horario', 'caso')

    proxima_cita = citas.filter(
        estado__in=['pendiente', 'confirmada'],
        horario__fecha__gt=hoy,
    ).order_by('horario__fecha', 'horario__hora_inicio').first()

    if not proxima_cita:
        proxima_cita = citas.filter(
            estado__in=['pendiente', 'confirmada'],
            horario__fecha=hoy,
            horario__hora_inicio__gt=ahora,
        ).order_by('horario__hora_inicio').first()

    casos = get_casos_queryset_for_user(request.user)

    return render(request, 'home.html', {
        'proxima_cita': proxima_cita,
        'casos': casos,
    })


@login_required
def estudiante_home_view(request):
    """Vista de home para estudiantes."""
    return home_view(request)


@login_required
def profesor_home_view(request):
    """Vista de home para profesores."""
    return home_view(request)


@login_required
def api_citas_estado_actual(request):
    """Endpoint JSON para polling del estado actual de citas."""
    base_citas = get_citas_queryset_for_user(request.user).select_related('horario', 'caso', 'beneficiario')

    hoy = timezone.localdate()
    ahora = timezone.localtime().time()

    proxima_cita = base_citas.filter(
        estado__in=['pendiente', 'confirmada'],
        horario__fecha__gt=hoy,
    ).order_by('horario__fecha', 'horario__hora_inicio').first()

    if not proxima_cita:
        proxima_cita = base_citas.filter(
            estado__in=['pendiente', 'confirmada'],
            horario__fecha=hoy,
            horario__hora_inicio__gt=ahora,
        ).order_by('horario__hora_inicio').first()

    historial_qs = base_citas.order_by('-fecha_creacion')
    estado_filtro = request.GET.get('estado')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sala_juridica = request.GET.get('sala_juridica')
    beneficiario_id = request.GET.get('beneficiario')

    if estado_filtro:
        historial_qs = historial_qs.filter(estado=estado_filtro)
    if fecha_inicio:
        historial_qs = historial_qs.filter(horario__fecha__gte=fecha_inicio)
    if fecha_fin:
        historial_qs = historial_qs.filter(horario__fecha__lte=fecha_fin)
    if sala_juridica:
        historial_qs = historial_qs.filter(caso__sala_juridica=sala_juridica)
    if beneficiario_id and request.user.rol in ['administrador', 'secretaria']:
        historial_qs = historial_qs.filter(beneficiario__pk=beneficiario_id)

    historial_citas = list(historial_qs)
    recordatorios_serializados = [serialize_cita(cita, request.user.rol) for cita in historial_citas]
    notificaciones = []

    if request.user.rol == RolChoices.SECRETARIA:
        notificaciones = list(
            Notificacion.objects.filter(usuario=request.user)
            .order_by('-fecha_creacion')[:10]
        )

    response = {
        'es_secretaria': request.user.rol == RolChoices.SECRETARIA,
        'citas': recordatorios_serializados,
        'cantidad_citas': len(recordatorios_serializados),
        'proxima_cita': serialize_cita(proxima_cita, request.user.rol),
        'historial_citas': recordatorios_serializados,
        'notificaciones': [serialize_notificacion(notificacion) for notificacion in notificaciones],
    }

    if len(historial_citas) == 0:
        response['mensaje'] = 'No existen citas registradas'

    return JsonResponse(response)


@login_required
def cancelar_cita_view(request, pk):
    """Vista para cancelar una cita.

    - Beneficiario: solo puede cancelar sus propias citas.
    - Secretaria / administrador: puede cancelar cualquier cita.
    """
    rol = request.user.rol

    if rol in ['administrador', 'secretaria']:
        cita = get_object_or_404(Cita, pk=pk)
    elif rol == 'beneficiario':
        cita = get_object_or_404(Cita, pk=pk, beneficiario=request.user)
    else:
        messages.error(request, 'No tiene permisos para cancelar citas.')
        return redirect('gestionar_citas')

    if request.method == "POST":
        try:
            motivo = request.POST.get('motivo', '').strip()
            cita.cambiar_estado('cancelada', usuario=request.user, motivo=motivo)
            notificar_cancelacion(cita)
            messages.success(request, 'Cita cancelada exitosamente. El horario ha sido liberado.')
        except ValidationError as e:
            messages.error(request, str(e.message))
        return redirect('gestionar_citas')

    return redirect('gestionar_citas')


@login_required
def posponer_cita_view(request, pk):
    """DEPRECADO: usar reagendar_cita_view.

    Esta vista se mantiene como alias compatible con codigo/templates legacy.
    Redirige a la nueva vista de reagendamiento.
    """
    messages.info(request, 'El flujo "Posponer" fue reemplazado por "Reagendar". Use el nuevo boton.')
    return redirect('gestionar_citas')


@login_required
def reagendar_cita_view(request, pk):
    """Vista para reagendar una cita de forma atomica.

    - Beneficiario: solo puede reagendar sus propias citas.
    - Secretaria / administrador: puede reagendar cualquier cita.
    - Profesor / estudiante: bloqueados.
    """
    rol = request.user.rol

    if rol in ['administrador', 'secretaria']:
        cita = get_object_or_404(Cita, pk=pk)
    elif rol == 'beneficiario':
        cita = get_object_or_404(Cita, pk=pk, beneficiario=request.user)
    else:
        messages.error(request, 'No tiene permisos para reagendar citas.')
        return redirect('gestionar_citas')

    if request.method == "POST":
        if not cita.puede_reagendar():
            messages.error(request, 'Esta cita no se puede reagendar.')
            return redirect('gestionar_citas')

        nuevo_horario_id = request.POST.get('nuevo_horario_id')
        if not nuevo_horario_id:
            messages.error(request, 'Debe seleccionar un nuevo horario.')
            return redirect('gestionar_citas')

        try:
            with transaction.atomic():
                nuevo_horario = HorarioDisponible.objects.select_for_update().get(
                    pk=nuevo_horario_id,
                )

                if not nuevo_horario.disponible:
                    raise ValidationError('El horario seleccionado ya no esta disponible.')

                inicio_nuevo = timezone.make_aware(
                    timezone.datetime.combine(nuevo_horario.fecha, nuevo_horario.hora_inicio)
                )
                if inicio_nuevo < timezone.now():
                    raise ValidationError('No se puede reagendar a un horario pasado.')

                horario_viejo = cita.horario
                cita.horario_anterior = horario_viejo
                cita.horario = nuevo_horario
                cita.fecha_reagendamiento = timezone.now()
                cita.reagendada_por = request.user
                cita.save()

                horario_viejo.disponible = True
                horario_viejo.save()

                nuevo_horario.disponible = False
                nuevo_horario.save()

            emitir_evento_calendario(cita, 'reagendada')
            notificar_reagendamiento_secretaria(cita)

            try:
                secretarias = Usuario.objects.filter(rol=RolChoices.SECRETARIA)
                crear_notificaciones_reagendamiento(cita=cita, destinatarios=secretarias)
            except Exception as e:
                logger.error("Error al notificar reagendamiento: %s", e)

            messages.success(
                request,
                f'Cita reagendada exitosamente para el {nuevo_horario.fecha} a las {nuevo_horario.hora_inicio}.',
            )
        except HorarioDisponible.DoesNotExist:
            messages.error(request, 'El horario seleccionado no existe.')
        except ValidationError as e:
            messages.error(request, str(e.message) if hasattr(e, 'message') else str(e))

        return redirect('gestionar_citas')

    return redirect('gestionar_citas')


@login_required
def confirmar_cita_view(request, pk):
    """Vista para confirmar una cita (HU2).

    - Beneficiario: solo puede confirmar sus propias citas.
    - Secretaria / administrador: puede confirmar cualquier cita.
    """
    rol = request.user.rol

    if rol in ['administrador', 'secretaria']:
        cita = get_object_or_404(Cita, pk=pk)
    elif rol == 'beneficiario':
        cita = get_object_or_404(Cita, pk=pk, beneficiario=request.user)
    else:
        messages.error(request, 'No tiene permisos para confirmar citas.')
        return redirect('gestionar_citas')

    if request.method == "POST":
        try:
            cita.cambiar_estado('confirmada')
            messages.success(request, 'Cita confirmada exitosamente.')
        except ValidationError as e:
            messages.error(request, str(e.message))
        return redirect('gestionar_citas')

    return redirect('gestionar_citas')


@login_required
def gestionar_citas_view(request):
    """Vista para gestionar citas (adaptada según rol)."""
    es_admin = request.user.rol in ['administrador', 'secretaria']

    hoy = timezone.localdate()
    ahora = timezone.localtime().time()

    # Filtros desde GET
    estado_filtro = request.GET.get('estado')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sala_juridica = request.GET.get('sala_juridica')
    beneficiario_id = request.GET.get('beneficiario')

    if es_admin:
        proxima_cita = Cita.objects.filter(
            estado__in=['pendiente', 'confirmada'],
        ).filter(
            horario__fecha__gt=hoy,
        ).select_related('horario', 'caso', 'beneficiario').order_by('horario__fecha', 'horario__hora_inicio').first()

        if not proxima_cita:
            proxima_cita = Cita.objects.filter(
                estado__in=['pendiente', 'confirmada'],
                horario__fecha=hoy,
                horario__hora_inicio__gt=ahora,
            ).select_related('horario', 'caso', 'beneficiario').order_by('horario__hora_inicio').first()

        # Querybase para historial (admin puede ver todo)
        historial_qs = Cita.objects.all().select_related('horario', 'caso', 'beneficiario')
        # aplicar filtros si vienen en GET
        if estado_filtro:
            historial_qs = historial_qs.filter(estado=estado_filtro)
        if fecha_inicio:
            historial_qs = historial_qs.filter(horario__fecha__gte=fecha_inicio)
        if fecha_fin:
            historial_qs = historial_qs.filter(horario__fecha__lte=fecha_fin)
        if sala_juridica:
            historial_qs = historial_qs.filter(caso__sala_juridica=sala_juridica)
        if beneficiario_id:
            historial_qs = historial_qs.filter(beneficiario__pk=beneficiario_id)

        historial_citas = historial_qs.order_by('-horario__fecha', '-horario__hora_inicio')
    else:
        proxima_cita = Cita.objects.filter(
            beneficiario=request.user,
            estado__in=['pendiente', 'confirmada'],
            horario__fecha__gt=hoy,
        ).select_related('horario', 'caso').order_by('horario__fecha', 'horario__hora_inicio').first()

        if not proxima_cita:
            proxima_cita = Cita.objects.filter(
                beneficiario=request.user,
                estado__in=['pendiente', 'confirmada'],
                horario__fecha=hoy,
                horario__hora_inicio__gt=ahora,
            ).select_related('horario', 'caso').order_by('horario__hora_inicio').first()

        # Para usuarios normales solo sus propias citas (ignorar filtros de beneficiario)
        historial_qs = Cita.objects.filter(beneficiario=request.user).select_related('horario', 'caso')
        if estado_filtro:
            historial_qs = historial_qs.filter(estado=estado_filtro)
        if fecha_inicio:
            historial_qs = historial_qs.filter(horario__fecha__gte=fecha_inicio)
        if fecha_fin:
            historial_qs = historial_qs.filter(horario__fecha__lte=fecha_fin)
        if sala_juridica:
            historial_qs = historial_qs.filter(caso__sala_juridica=sala_juridica)
        historial_citas = historial_qs.order_by('-horario__fecha', '-horario__hora_inicio')

    cita_seleccionada = None
    cita_id = request.GET.get('cita_id')
    if cita_id:
        if es_admin:
            cita_seleccionada = Cita.objects.filter(
                pk=cita_id,
            ).select_related('horario', 'caso', 'beneficiario').first()
        else:
            cita_seleccionada = Cita.objects.filter(
                pk=cita_id,
                beneficiario=request.user,
            ).select_related('horario', 'caso').first()

    horarios_disponibles = HorarioDisponible.objects.filter(
        disponible=True,
        fecha__gte=hoy,
    ).order_by('fecha', 'hora_inicio')

    notificaciones = Notificacion.objects.none()
    if request.user.rol == RolChoices.SECRETARIA:
        notificaciones = Notificacion.objects.filter(
            usuario=request.user,
        ).order_by('-fecha_creacion')[:10]

    # Opciones para selects en template
    estados = [c[0] for c in Cita.ESTADO_CHOICES]
    salas = [s[0] for s in Caso.SALA_CHOICES]
    beneficiarios = Usuario.objects.filter(rol=RolChoices.BENEFICIARIO) if es_admin else None

    return render(request, 'citas/gestionar_citas.html', {
        'proxima_cita': proxima_cita,
        'historial_citas': historial_citas,
        'cita_seleccionada': cita_seleccionada,
        'es_admin': es_admin,
        'horarios_disponibles': horarios_disponibles,
        'notificaciones': notificaciones,
        'filtros': {
            'estado': estado_filtro,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'sala_juridica': sala_juridica,
            'beneficiario': beneficiario_id,
        },
        'estados_choices': estados,
        'salas_choices': salas,
        'beneficiarios': beneficiarios,
    })


@login_required
def gestionar_casos_view(request):
    """Vista para gestionar casos y pedir citas."""
    casos = get_casos_queryset_for_user(request.user)

    caso_seleccionado = None
    caso_id = request.GET.get('caso_id')
    if caso_id:
        caso_seleccionado = get_casos_queryset_for_user(request.user).filter(
            pk=caso_id,
        ).first()

    horarios_disponibles = HorarioDisponible.objects.filter(disponible=True)

    return render(request, 'citas/gestionar_casos.html', {
        'casos': casos,
        'caso_seleccionado': caso_seleccionado,
        'horarios_disponibles': horarios_disponibles,
    })


@login_required
def historial_usuario_view(request, usuario_id):
    """Permite a administradores/secretaria consultar el historial de citas de un usuario.

    Muestra lista ordenada por fecha (más reciente primero) con fecha, estado y tipo.
    """
    if request.user.rol not in ['administrador', 'secretaria']:
        return HttpResponseForbidden('No tiene permisos para ver historiales de usuarios.')

    usuario = get_object_or_404(Usuario, pk=usuario_id)

    citas_qs = Cita.objects.filter(
        Q(beneficiario=usuario) | Q(caso__estudiante_asignado=usuario)
    ).select_related('horario', 'caso', 'beneficiario').order_by('-horario__fecha', '-horario__hora_inicio')

    # Serializar lo mínimo requerido por la HU
    historial = []
    for cita in citas_qs:
        fecha = cita.horario.fecha.strftime('%d/%m/%Y')
        hora = cita.horario.hora_inicio.strftime('%H:%M')
        historial.append({
            'fecha': fecha,
            'hora': hora,
            'estado': cita.get_estado_display(),
            'tipo': cita.get_tipo_atencion_display(),
            'caso_codigo': cita.caso.codigo if cita.caso else None,
        })

    return render(request, 'citas/historial_usuario.html', {
        'usuario_obj': usuario,
        'historial': historial,
    })


@login_required
def agendar_cita_view(request):
    """Vista para agendar una nueva cita asociada a un caso (HU10).

    Aplica validación atómica de disponibilidad usando select_for_update
    para prevenir race conditions ante agendamientos simultáneos sobre
    el mismo horario.
    """
    if request.method == "POST":
        caso_id = request.POST.get('caso_id')
        fecha_str = request.POST.get('fecha')
        hora_str = request.POST.get('hora')
        tipo_atencion = request.POST.get('tipo_atencion')

        caso = get_object_or_404(Caso, pk=caso_id, beneficiario=request.user)

        from datetime import datetime
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hora = datetime.strptime(hora_str, '%H:%M').time()
        except (ValueError, TypeError):
            messages.error(request, 'Fecha u hora inválida. Intente de nuevo.')
            return redirect(f'/gestionar-casos/?caso_id={caso_id}')

        try:
            with transaction.atomic():
                horario = HorarioDisponible.objects.select_for_update().filter(
                    fecha=fecha,
                    hora_inicio__hour=hora.hour,
                    hora_inicio__minute=hora.minute,
                ).first()

                if not horario:
                    raise ValidationError('Ese horario no existe.')

                if not horario.disponible:
                    raise ValidationError('Ese horario ya no está disponible. Seleccione otro.')

                inicio_horario = timezone.make_aware(
                    datetime.combine(horario.fecha, horario.hora_inicio)
                )
                if inicio_horario < timezone.now():
                    raise ValidationError('No se puede agendar a un horario pasado.')

                cita_existente = Cita.objects.filter(
                    caso=caso,
                    estado__in=['pendiente', 'confirmada'],
                ).exists()

                if cita_existente:
                    raise ValidationError(
                        f'El caso {caso.codigo} ya tiene una cita activa. '
                        'Cancele o espere a que se complete antes de agendar otra.'
                    )

                cita = Cita.objects.create(
                    beneficiario=request.user,
                    caso=caso,
                    horario=horario,
                    tipo_atencion=tipo_atencion,
                )

                horario.disponible = False
                horario.save()

            try:
                enviar_correo_recordatorio(cita)
                messages.success(
                    request,
                    f'Cita solicitada exitosamente para el caso {caso.codigo}. Se ha enviado un recordatorio al correo del beneficiario.',
                )
            except Exception:
                messages.success(
                    request,
                    f'Cita solicitada exitosamente para el caso {caso.codigo}. No se pudo enviar el correo de recordatorio, pero la cita fue registrada.',
                )
            return redirect('gestionar_citas')

        except ValidationError as e:
            messages.error(request, str(e.message) if hasattr(e, 'message') else str(e))
            return redirect(f'/gestionar-casos/?caso_id={caso_id}')

    return redirect('gestionar_casos')


@login_required
def marcar_asistencia_view(request, pk):
    """Vista para marcar asistencia o inasistencia (HU3 - solo secretaria/admin)."""
    if request.user.rol not in ['administrador', 'secretaria']:
        messages.error(request, 'No tiene permisos para realizar esta acción.')
        return redirect('gestionar_citas')

    cita = get_object_or_404(Cita, pk=pk)

    if request.method == "POST":
        accion = request.POST.get('accion')

        if cita.estado != 'confirmada':
            messages.error(request, 'Solo se puede marcar asistencia en citas confirmadas.')
            return redirect(f'/gestionar-citas/?cita_id={pk}')

        from .models import RegistroAsistencia

        if accion == 'asistio':
            cita.cambiar_estado('cumplida')
            RegistroAsistencia.objects.create(
                cita=cita,
                asistio=True,
                registrado_por=request.user,
            )
            messages.success(request, 'Asistencia registrada exitosamente.')
        elif accion == 'no_asistio':
            cita.cambiar_estado('no_asistio')
            RegistroAsistencia.objects.create(
                cita=cita,
                asistio=False,
                registrado_por=request.user,
            )
            messages.success(request, 'Inasistencia registrada exitosamente.')

        return redirect(f'/gestionar-citas/?cita_id={pk}')

    return redirect('gestionar_citas')