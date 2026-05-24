from citas.models import RegistroAsistencia


def obtener_datos_reporte_asistencia(filtros=None):
    """Obtiene los registros de asistencia para el reporte.

    Parametros:
        filtros (dict | None): Diccionario opcional con filtros para el
            queryset. Soporta las claves `fecha_inicio`, `fecha_fin` y
            `sala_juridica`.

    Filtros disponibles:
        fecha_inicio: Fecha minima para `cita__horario__fecha`.
        fecha_fin: Fecha maxima para `cita__horario__fecha`.
        sala_juridica: Valor de `cita__caso__sala_juridica`.

    Retorna:
        QuerySet: QuerySet de `RegistroAsistencia` con relaciones cargadas y
        ordenado por `cita__horario__fecha` descendente.
    """
    queryset = RegistroAsistencia.objects.select_related(
        'cita',
        'cita__beneficiario',
        'cita__caso',
        'cita__horario',
        'registrado_por',
    )

    if filtros:
        fecha_inicio = filtros.get('fecha_inicio')
        fecha_fin = filtros.get('fecha_fin')
        sala_juridica = filtros.get('sala_juridica')
        estudiante_id = filtros.get('estudiante_id')

        if fecha_inicio:
            queryset = queryset.filter(cita__horario__fecha__gte=fecha_inicio)

        if fecha_fin:
            queryset = queryset.filter(cita__horario__fecha__lte=fecha_fin)

        if sala_juridica:
            queryset = queryset.filter(cita__caso__sala_juridica=sala_juridica)

        if estudiante_id:
            queryset = queryset.filter(cita__caso__estudiante_asignado_id=estudiante_id)

    return queryset.order_by('-cita__horario__fecha')


from decimal import Decimal, ROUND_HALF_UP
from .models import MetricasAsistencia
from citas.models import Cita


def generar_metricas_asistencia() -> MetricasAsistencia | None:
    """Calcula y persiste métricas de asistencia/inasistencia.

    Retorna la instancia creada o None si no hay datos para calcular.
    """
    queryset = Cita.objects.filter(estado__in=['cumplida', 'no_asistio'])
    total = queryset.count()
    if total == 0:
        return None

    asistidas = queryset.filter(estado='cumplida').count()
    no_asistio = queryset.filter(estado='no_asistio').count()

    porcentaje_asistencia = (Decimal(asistidas) / Decimal(total) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    porcentaje_inasistencia = (Decimal(no_asistio) / Decimal(total) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    objeto = MetricasAsistencia.objects.create(
        total_citas=total,
        asistidas_count=asistidas,
        no_asistio_count=no_asistio,
        porcentaje_asistencia=porcentaje_asistencia,
        porcentaje_inasistencia=porcentaje_inasistencia,
    )

    return objeto