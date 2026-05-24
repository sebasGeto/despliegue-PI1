from django.core.management.base import BaseCommand
from reportes.services import generar_metricas_asistencia


class Command(BaseCommand):
    help = 'Genera métricas de asistencia e inasistencia y las guarda en reportes'

    def handle(self, *args, **options):
        resultado = generar_metricas_asistencia()
        if resultado is None:
            self.stdout.write(self.style.WARNING('No hay citas finalizadas para generar métricas.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Métricas generadas: total={resultado.total_citas}, asistidas={resultado.asistidas_count}, no_asistio={resultado.no_asistio_count}'))
