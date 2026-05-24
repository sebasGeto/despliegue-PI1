from django.contrib import admin
from .models import MetricasAsistencia


@admin.register(MetricasAsistencia)
class MetricasAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('fecha_generacion', 'total_citas', 'asistidas_count', 'no_asistio_count', 'porcentaje_asistencia', 'porcentaje_inasistencia')
    readonly_fields = ('fecha_generacion',)
    ordering = ('-fecha_generacion',)
