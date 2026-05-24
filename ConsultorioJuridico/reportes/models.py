from django.db import models


class MetricasAsistencia(models.Model):
	"""Almacena métricas de asistencia/inasistencia calculadas automáticamente.

	Se guarda un registro cada vez que se generan métricas; la aplicación
	puede consultar el último registro para mostrar estadísticas actualizadas.
	"""
	fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de generación')
	total_citas = models.IntegerField(verbose_name='Total de citas', default=0)
	asistidas_count = models.IntegerField(verbose_name='Citas asistidas', default=0)
	no_asistio_count = models.IntegerField(verbose_name='Citas no asistidas', default=0)
	porcentaje_asistencia = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje asistencia', default=0)
	porcentaje_inasistencia = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Porcentaje inasistencia', default=0)

	class Meta:
		verbose_name = 'Métricas de asistencia'
		verbose_name_plural = 'Métricas de asistencia'
		ordering = ['-fecha_generacion']

	def __str__(self):
		return f'Métricas {self.fecha_generacion} - asistencia {self.porcentaje_asistencia}%'
