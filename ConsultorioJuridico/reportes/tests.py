from datetime import date, time, timedelta
import uuid

from django.test import Client, TestCase
from django.urls import reverse

from citas.models import Caso, Cita, HorarioDisponible, RegistroAsistencia
from reportes.services import obtener_datos_reporte_asistencia
from usuarios.models import Usuario


def crear_usuario(documento, rol, nombre_completo=None):
	nombre = nombre_completo or f'Usuario {documento}'
	return Usuario.objects.create_user(
		documento=documento,
		correo=f'{documento}@test.local',
		nombre_completo=nombre,
		password='testpass123',
		rol=rol,
	)


def crear_horario(fecha=None):
	return HorarioDisponible.objects.create(
		fecha=fecha or date.today(),
		hora_inicio=time(10, 0),
		hora_fin=time(11, 0),
	)


def crear_caso(beneficiario, sala='civil'):
	return Caso.objects.create(
		codigo=f'CASO-{uuid.uuid4().hex[:10]}',
		beneficiario=beneficiario,
		sala_juridica=sala,
		descripcion='Caso de prueba',
	)


def crear_cita(beneficiario, horario, caso=None):
	return Cita.objects.create(
		beneficiario=beneficiario,
		horario=horario,
		caso=caso,
		tipo_atencion='presencial',
		estado='cumplida',
	)


def crear_registro(cita, asistio=True, registrado_por=None):
	return RegistroAsistencia.objects.create(
		cita=cita,
		asistio=asistio,
		registrado_por=registrado_por,
	)


class ExportarReportePDFTest(TestCase):
	def setUp(self):
		self.client = Client()
		self.url = reverse('reportes:exportar_pdf')
		self.secretaria = crear_usuario('sec-pdf', 'secretaria', 'Secretaria PDF')
		self.admin = crear_usuario('adm-pdf', 'administrador', 'Admin PDF')
		self.beneficiario = crear_usuario('ben-pdf', 'beneficiario', 'Beneficiario PDF')
		self.estudiante = crear_usuario('est-pdf', 'estudiante', 'Estudiante PDF')
		self.profesor = crear_usuario('pro-pdf', 'profesor', 'Profesor PDF')

	def test_acceso_denegado_beneficiario(self):
		self.client.force_login(self.beneficiario)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_acceso_denegado_estudiante(self):
		self.client.force_login(self.estudiante)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_acceso_denegado_profesor(self):
		self.client.force_login(self.profesor)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_redirige_si_no_autenticado(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 302)

	def test_secretaria_puede_exportar_pdf(self):
		self.client.force_login(self.secretaria)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('application/pdf', response['Content-Type'])

	def test_administrador_puede_exportar_pdf(self):
		self.client.force_login(self.admin)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('application/pdf', response['Content-Type'])

	def test_pdf_con_registros_vacios(self):
		self.client.force_login(self.secretaria)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('application/pdf', response['Content-Type'])

	def test_pdf_con_registros(self):
		horario = crear_horario()
		caso = crear_caso(self.beneficiario, sala='civil')
		cita = crear_cita(self.beneficiario, horario, caso=caso)
		crear_registro(cita, registrado_por=self.secretaria)

		self.client.force_login(self.secretaria)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('application/pdf', response['Content-Type'])

	def test_pdf_con_filtro_fecha_inicio(self):
		horario = crear_horario(fecha=date.today())
		caso = crear_caso(self.beneficiario, sala='civil')
		cita = crear_cita(self.beneficiario, horario, caso=caso)
		crear_registro(cita, registrado_por=self.secretaria)

		self.client.force_login(self.secretaria)
		response = self.client.get(self.url, {'fecha_inicio': date.today().isoformat()})
		self.assertEqual(response.status_code, 200)

	def test_pdf_con_filtro_sala_juridica(self):
		horario = crear_horario()
		caso = crear_caso(self.beneficiario, sala='civil')
		cita = crear_cita(self.beneficiario, horario, caso=caso)
		crear_registro(cita, registrado_por=self.secretaria)

		self.client.force_login(self.secretaria)
		response = self.client.get(self.url, {'sala_juridica': 'civil'})
		self.assertEqual(response.status_code, 200)


class ExportarReporteExcelTest(TestCase):
	def setUp(self):
		self.client = Client()
		self.url = reverse('reportes:exportar_excel')
		self.secretaria = crear_usuario('sec-xls', 'secretaria', 'Secretaria XLS')
		self.admin = crear_usuario('adm-xls', 'administrador', 'Admin XLS')
		self.beneficiario = crear_usuario('ben-xls', 'beneficiario', 'Beneficiario XLS')
		self.estudiante = crear_usuario('est-xls', 'estudiante', 'Estudiante XLS')
		self.profesor = crear_usuario('pro-xls', 'profesor', 'Profesor XLS')

	def test_acceso_denegado_beneficiario(self):
		self.client.force_login(self.beneficiario)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_acceso_denegado_estudiante(self):
		self.client.force_login(self.estudiante)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_acceso_denegado_profesor(self):
		self.client.force_login(self.profesor)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 403)

	def test_redirige_si_no_autenticado(self):
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 302)

	def test_secretaria_puede_exportar_excel(self):
		self.client.force_login(self.secretaria)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('spreadsheetml', response['Content-Type'])

	def test_administrador_puede_exportar_excel(self):
		self.client.force_login(self.admin)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('spreadsheetml', response['Content-Type'])

	def test_excel_con_registros_vacios(self):
		self.client.force_login(self.secretaria)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('spreadsheetml', response['Content-Type'])

	def test_excel_con_registros(self):
		horario = crear_horario()
		caso = crear_caso(self.beneficiario, sala='laboral')
		cita = crear_cita(self.beneficiario, horario, caso=caso)
		crear_registro(cita, registrado_por=self.secretaria)

		self.client.force_login(self.secretaria)
		response = self.client.get(self.url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('spreadsheetml', response['Content-Type'])

	def test_excel_con_filtro_fecha_fin(self):
		horario = crear_horario(fecha=date.today())
		caso = crear_caso(self.beneficiario, sala='civil')
		cita = crear_cita(self.beneficiario, horario, caso=caso)
		crear_registro(cita, registrado_por=self.secretaria)

		self.client.force_login(self.secretaria)
		response = self.client.get(self.url, {'fecha_fin': date.today().isoformat()})
		self.assertEqual(response.status_code, 200)

	def test_excel_con_filtro_sala_juridica(self):
		horario = crear_horario()
		caso = crear_caso(self.beneficiario, sala='laboral')
		cita = crear_cita(self.beneficiario, horario, caso=caso)
		crear_registro(cita, registrado_por=self.secretaria)

		self.client.force_login(self.secretaria)
		response = self.client.get(self.url, {'sala_juridica': 'laboral'})
		self.assertEqual(response.status_code, 200)


class ObtenerDatosReporteServiceTest(TestCase):
	def setUp(self):
		self.secretaria = crear_usuario('sec-svc', 'secretaria', 'Secretaria SVC')
		self.beneficiario = crear_usuario('ben-svc', 'beneficiario', 'Beneficiario SVC')

	def test_retorna_todos_los_registros_sin_filtros(self):
		for dias in [0, 1, 2]:
			horario = crear_horario(fecha=date.today() - timedelta(days=dias))
			caso = crear_caso(self.beneficiario, sala='civil')
			cita = crear_cita(self.beneficiario, horario, caso=caso)
			crear_registro(cita, registrado_por=self.secretaria)

		qs = obtener_datos_reporte_asistencia()
		self.assertEqual(qs.count(), 3)

	def test_filtro_fecha_inicio(self):
		hoy = date.today()
		ayer = hoy - timedelta(days=1)

		cita_hoy = crear_cita(
			self.beneficiario,
			crear_horario(fecha=hoy),
			caso=crear_caso(self.beneficiario, sala='civil'),
		)
		crear_registro(cita_hoy, registrado_por=self.secretaria)

		cita_ayer = crear_cita(
			self.beneficiario,
			crear_horario(fecha=ayer),
			caso=crear_caso(self.beneficiario, sala='civil'),
		)
		crear_registro(cita_ayer, registrado_por=self.secretaria)

		qs = obtener_datos_reporte_asistencia({'fecha_inicio': hoy})
		self.assertEqual(qs.count(), 1)

	def test_filtro_fecha_fin(self):
		hoy = date.today()
		manana = hoy + timedelta(days=1)

		cita_hoy = crear_cita(
			self.beneficiario,
			crear_horario(fecha=hoy),
			caso=crear_caso(self.beneficiario, sala='civil'),
		)
		crear_registro(cita_hoy, registrado_por=self.secretaria)

		cita_manana = crear_cita(
			self.beneficiario,
			crear_horario(fecha=manana),
			caso=crear_caso(self.beneficiario, sala='civil'),
		)
		crear_registro(cita_manana, registrado_por=self.secretaria)

		qs = obtener_datos_reporte_asistencia({'fecha_fin': hoy})
		self.assertEqual(qs.count(), 1)

	def test_filtro_sala_juridica(self):
		cita_civil = crear_cita(
			self.beneficiario,
			crear_horario(),
			caso=crear_caso(self.beneficiario, sala='civil'),
		)
		crear_registro(cita_civil, registrado_por=self.secretaria)

		cita_penal = crear_cita(
			self.beneficiario,
			crear_horario(fecha=date.today() - timedelta(days=1)),
			caso=crear_caso(self.beneficiario, sala='penal'),
		)
		crear_registro(cita_penal, registrado_por=self.secretaria)

		qs = obtener_datos_reporte_asistencia({'sala_juridica': 'civil'})
		self.assertEqual(qs.count(), 1)

	def test_filtro_sala_excluye_citas_sin_caso(self):
		cita_sin_caso = crear_cita(self.beneficiario, crear_horario(), caso=None)
		crear_registro(cita_sin_caso, registrado_por=self.secretaria)

		qs = obtener_datos_reporte_asistencia({'sala_juridica': 'civil'})
		self.assertEqual(qs.count(), 0)

	def test_orden_descendente_por_fecha(self):
		reciente = date.today()
		antigua = reciente - timedelta(days=3)

		cita_antigua = crear_cita(
			self.beneficiario,
			crear_horario(fecha=antigua),
			caso=crear_caso(self.beneficiario, sala='civil'),
		)
		crear_registro(cita_antigua, registrado_por=self.secretaria)

		cita_reciente = crear_cita(
			self.beneficiario,
			crear_horario(fecha=reciente),
			caso=crear_caso(self.beneficiario, sala='laboral'),
		)
		crear_registro(cita_reciente, registrado_por=self.secretaria)

		qs = obtener_datos_reporte_asistencia()
		self.assertEqual(qs.first().cita.horario.fecha, reciente)

	def test_retorna_queryset_vacio_si_no_hay_registros(self):
		qs = obtener_datos_reporte_asistencia()
		self.assertEqual(qs.count(), 0)
