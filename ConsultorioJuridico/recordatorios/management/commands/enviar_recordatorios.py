"""
Comando de gestión para enviar recordatorios de citas.
HU6 - Envío automático de recordatorios.
"""
from django.core.management.base import BaseCommand
from recordatorios.services import procesar_recordatorios


class Command(BaseCommand):
    """
    Comando Django para procesar y enviar recordatorios de citas.
    
    Uso:
        python manage.py enviar_recordatorios
    """
    help = 'Procesa y envía recordatorios de citas confirmadas en las próximas 24 horas'

    def handle(self, *args, **options):
        """
        Ejecuta el procesamiento de recordatorios.
        
        Muestra información sobre el número de citas procesadas.
        """
        self.stdout.write(self.style.NOTICE('Iniciando procesamiento de recordatorios...'))
        
        try:
            citas_procesadas = procesar_recordatorios()
            
            if citas_procesadas > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Se procesaron {citas_procesadas} cita(s) exitosamente.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('No se encontraron citas elegibles para enviar recordatorios.')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al procesar recordatorios: {str(e)}')
            )
            raise
        
        self.stdout.write(self.style.SUCCESS('Procesamiento de recordatorios completado.'))