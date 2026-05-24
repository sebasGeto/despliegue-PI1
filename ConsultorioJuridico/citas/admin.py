from django.contrib import admin
from .models import HorarioDisponible, Cita, RegistroAsistencia, Caso


@admin.register(Caso)
class CasoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'beneficiario', 'sala_juridica', 'estado', 'fecha_creacion')
    list_filter = ('sala_juridica', 'estado')
    search_fields = ('codigo', 'beneficiario__documento', 'beneficiario__nombre_completo')


@admin.register(HorarioDisponible)
class HorarioDisponibleAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'hora_inicio', 'hora_fin', 'disponible')
    list_filter = ('disponible', 'fecha')
    list_editable = ('disponible',)


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'beneficiario', 'caso', 'horario', 'tipo_atencion',
        'estado', 'fecha_creacion', 'fecha_cancelacion', 'cancelada_por',
    )
    list_filter = ('estado', 'tipo_atencion')
    search_fields = (
        'beneficiario__documento', 'beneficiario__nombre_completo',
        'cancelada_por__documento', 'motivo_cancelacion',
    )
    readonly_fields = (
        'fecha_creacion', 'fecha_confirmacion',
        'fecha_cancelacion', 'cancelada_por', 'motivo_cancelacion',
    )


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('cita', 'asistio', 'registrado_por', 'fecha_registro')
    list_filter = ('asistio',)