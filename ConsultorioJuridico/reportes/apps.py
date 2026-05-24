from django.apps import AppConfig


class ReportesConfig(AppConfig):
    name = 'reportes'

    def ready(self):
        # Importar señales para conectar el receptor de Cita
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
