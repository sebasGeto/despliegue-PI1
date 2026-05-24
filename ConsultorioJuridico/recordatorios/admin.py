from django.contrib import admin
from .models import LogRecordatorio


@admin.register(LogRecordatorio)
class LogRecordatorioAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo LogRecordatorio.
    Muestra los logs de intentos de envío de recordatorios.
    """
    list_display = ['cita', 'canal', 'estado', 'fecha_intento', 'fecha_envio']
    list_filter = ['canal', 'estado', 'fecha_intento']
    search_fields = ['cita__id', 'mensaje_error']
    readonly_fields = ['fecha_intento']
    
    fieldsets = (
        ('Información de la Cita', {
            'fields': ('cita',)
        }),
        ('Detalles del Envío', {
            'fields': ('canal', 'estado', 'fecha_intento', 'fecha_envio', 'mensaje_error')
        }),
    )
