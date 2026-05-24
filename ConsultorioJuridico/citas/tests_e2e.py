from datetime import date, time, timedelta

from django.test import TestCase

from citas.models import Caso, Cita, HorarioDisponible, RegistroAsistencia
from notificaciones.models import Notificacion
from usuarios.models import RolChoices, Usuario


def crear_usuario(documento, rol, nombre_completo=None, password='testpass123'):
    nombre = nombre_completo or f'Usuario {documento}'
    return Usuario.objects.create_user(
        documento=documento,
        correo=f'{documento}@test.com',
        nombre_completo=nombre,
        password=password,
        rol=rol,
    )


def crear_horario(fecha=None, disponible=True):
    fecha = fecha or (date.today() + timedelta(days=7))
    return HorarioDisponible.objects.create(
        fecha=fecha,
        hora_inicio=time(10, 0),
        hora_fin=time(11, 0),
        disponible=disponible,
    )


def crear_caso(beneficiario, sala='civil', codigo=None):
    codigo = codigo or f'CASO-{beneficiario.documento}-{Caso.objects.count() + 1}'
    return Caso.objects.create(
        codigo=codigo,
        beneficiario=beneficiario,
        sala_juridica=sala,
        descripcion='Caso E2E',
    )


def crear_cita(beneficiario, horario, caso=None, estado='pendiente'):
    cita = Cita.objects.create(
        beneficiario=beneficiario,
        horario=horario,
        caso=caso,
        tipo_atencion='presencial',
        estado='pendiente',
    )
    if estado != 'pendiente':
        cita.estado = estado
        cita.save(update_fields=['estado'])
    return cita


def crear_registro(cita, asistio=True, registrado_por=None):
    return RegistroAsistencia.objects.create(
        cita=cita,
        asistio=asistio,
        registrado_por=registrado_por,
    )


def login_cliente(client, documento, password='testpass123'):
    return client.post('/login/', {'documento': documento, 'password': password}, follow=True)


class E2E_01_RegistroTest(TestCase):
    def setUp(self):
        self.documento = 'REG001'
        self.password = 'testpass123'

    def test_registro_completo_dos_pasos(self):
        response_paso1 = self.client.post(
            '/registro/',
            {
                'documento': self.documento,
                'nombre_completo': 'Beneficiario Registro',
                'telefono': '3001234567',
                'correo': 'reg001@test.com',
                'direccion': 'Calle 1 # 2-3',
            },
            follow=True,
        )
        self.assertEqual(response_paso1.status_code, 200)

        response_paso2 = self.client.post(
            '/registro/paso2/',
            {
                'password1': self.password,
                'password2': self.password,
                'acepta_tratamiento_datos': True,
            },
            follow=True,
        )
        self.assertEqual(response_paso2.status_code, 200)

        usuario = Usuario.objects.get(documento=self.documento)
        self.assertEqual(usuario.rol, RolChoices.BENEFICIARIO)

        login_response = login_cliente(self.client, self.documento, self.password)
        self.assertEqual(login_response.status_code, 200)
        self.assertIsNotNone(self.client.session.get('_auth_user_id'))


class E2E_02_LoginLogoutTest(TestCase):
    def setUp(self):
        self.admin = crear_usuario('ADM001', RolChoices.ADMINISTRADOR)
        self.secretaria = crear_usuario('SEC001', RolChoices.SECRETARIA)
        self.beneficiario = crear_usuario('BEN001', RolChoices.BENEFICIARIO)

    def test_login_administrador(self):
        response = login_cliente(self.client, self.admin.documento)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/home/')
        self.assertIsNotNone(self.client.session.get('_auth_user_id'))

    def test_login_secretaria(self):
        response = login_cliente(self.client, self.secretaria.documento)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/home/')
        self.assertIsNotNone(self.client.session.get('_auth_user_id'))

    def test_login_beneficiario(self):
        response = login_cliente(self.client, self.beneficiario.documento)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/home/')
        self.assertIsNotNone(self.client.session.get('_auth_user_id'))

    def test_login_credenciales_invalidas(self):
        response = self.client.post(
            '/login/',
            {'documento': self.beneficiario.documento, 'password': 'incorrecta'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request['PATH_INFO'], '/login/')
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_logout_elimina_sesion(self):
        login_cliente(self.client, self.beneficiario.documento)
        self.assertIsNotNone(self.client.session.get('_auth_user_id'))

        logout_response = self.client.get('/logout/', follow=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(logout_response.request['PATH_INFO'], '/login/')

        home_response = self.client.get('/home/')
        self.assertEqual(home_response.status_code, 302)
        self.assertTrue(home_response.url.startswith('/login/'))

    def test_acceso_sin_sesion_redirige_login(self):
        response = self.client.get('/home/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))


class E2E_03_AgendarCitaTest(TestCase):
    def setUp(self):
        self.beneficiario = crear_usuario('BEN010', RolChoices.BENEFICIARIO)
        self.caso = crear_caso(self.beneficiario, codigo='CASO-E2E-AG-1')

    def test_beneficiario_agenda_cita(self):
        horario = crear_horario(fecha=date.today() + timedelta(days=8), disponible=True)
        login_cliente(self.client, self.beneficiario.documento)

        response = self.client.post(
            '/agendar-cita/',
            {
                'caso_id': self.caso.pk,
                'horario_id': horario.pk,
                'fecha': horario.fecha.strftime('%Y-%m-%d'),
                'hora': horario.hora_inicio.strftime('%H:%M'),
                'tipo_atencion': 'presencial',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        cita = Cita.objects.get(caso=self.caso)
        self.assertEqual(cita.estado, 'pendiente')
        horario.refresh_from_db()
        self.assertFalse(horario.disponible)

    def test_no_puede_agendar_segunda_cita_activa_mismo_caso(self):
        horario_activo = crear_horario(fecha=date.today() + timedelta(days=8), disponible=True)
        cita = crear_cita(self.beneficiario, horario_activo, caso=self.caso, estado='pendiente')
        horario_activo.disponible = False
        horario_activo.save(update_fields=['disponible'])

        horario_nuevo = crear_horario(fecha=date.today() + timedelta(days=9), disponible=True)
        login_cliente(self.client, self.beneficiario.documento)

        response = self.client.post(
            '/agendar-cita/',
            {
                'caso_id': self.caso.pk,
                'horario_id': horario_nuevo.pk,
                'fecha': horario_nuevo.fecha.strftime('%Y-%m-%d'),
                'hora': horario_nuevo.hora_inicio.strftime('%H:%M'),
                'tipo_atencion': 'presencial',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cita.objects.filter(caso=self.caso).count(), 1)
        self.assertEqual(Cita.objects.get(pk=cita.pk).estado, 'pendiente')


class E2E_04_ConfirmarCitaTest(TestCase):
    def setUp(self):
        self.beneficiario = crear_usuario('BEN020', RolChoices.BENEFICIARIO)
        self.horario = crear_horario(fecha=date.today() + timedelta(days=8), disponible=False)
        self.caso = crear_caso(self.beneficiario, codigo='CASO-E2E-CF-1')
        self.cita = crear_cita(self.beneficiario, self.horario, caso=self.caso, estado='pendiente')

    def test_beneficiario_confirma_cita_pendiente(self):
        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.post(f'/citas/{self.cita.pk}/confirmar/', follow=True)
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'confirmada')

    def test_no_puede_confirmar_cita_ya_confirmada(self):
        self.cita.estado = 'confirmada'
        self.cita.save(update_fields=['estado'])

        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.post(f'/citas/{self.cita.pk}/confirmar/', follow=True)
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'confirmada')


class E2E_05_CancelarCitaTest(TestCase):
    def setUp(self):
        self.beneficiario = crear_usuario('BEN030', RolChoices.BENEFICIARIO)
        self.otro_beneficiario = crear_usuario('BEN031', RolChoices.BENEFICIARIO)
        self.secretaria = crear_usuario('SEC030', RolChoices.SECRETARIA)
        self.estudiante = crear_usuario('EST030', RolChoices.ESTUDIANTE)

        self.horario = crear_horario(fecha=date.today() + timedelta(days=8), disponible=False)
        self.caso = crear_caso(self.beneficiario, codigo='CASO-E2E-CA-1')
        self.cita = crear_cita(self.beneficiario, self.horario, caso=self.caso, estado='pendiente')

    def test_beneficiario_cancela_su_cita(self):
        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/cancelar/',
            {'motivo': 'No puedo asistir'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.horario.refresh_from_db()
        self.assertEqual(self.cita.estado, 'cancelada')
        self.assertTrue(self.horario.disponible)

    def test_secretaria_cancela_cita_de_otro_beneficiario(self):
        login_cliente(self.client, self.secretaria.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/cancelar/',
            {'motivo': 'Cancelada por secretaria'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'cancelada')

    def test_estudiante_no_puede_cancelar_cita(self):
        login_cliente(self.client, self.estudiante.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/cancelar/',
            {'motivo': 'Intento sin permisos'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'pendiente')


class E2E_06_ReagendarCitaTest(TestCase):
    def setUp(self):
        self.beneficiario = crear_usuario('BEN040', RolChoices.BENEFICIARIO)
        self.caso = crear_caso(self.beneficiario, codigo='CASO-E2E-RE-1')
        self.horario_original = crear_horario(fecha=date.today() + timedelta(days=8), disponible=False)
        self.cita = crear_cita(self.beneficiario, self.horario_original, caso=self.caso, estado='pendiente')

    def test_beneficiario_reagenda_cita(self):
        nuevo_horario = crear_horario(fecha=date.today() + timedelta(days=9), disponible=True)
        login_cliente(self.client, self.beneficiario.documento)

        response = self.client.post(
            f'/citas/{self.cita.pk}/reagendar/',
            {'nuevo_horario_id': nuevo_horario.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.horario_original.refresh_from_db()
        nuevo_horario.refresh_from_db()

        self.assertEqual(self.cita.horario_id, nuevo_horario.pk)
        self.assertTrue(self.horario_original.disponible)
        self.assertFalse(nuevo_horario.disponible)

    def test_no_puede_reagendar_a_horario_ocupado(self):
        horario_ocupado = crear_horario(fecha=date.today() + timedelta(days=9), disponible=False)
        horario_original_id = self.cita.horario_id

        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/reagendar/',
            {'nuevo_horario_id': horario_ocupado.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario_id, horario_original_id)


class E2E_07_NotificacionReagendamientoTest(TestCase):
    def setUp(self):
        self.secretaria = crear_usuario('SEC050', RolChoices.SECRETARIA, nombre_completo='Secretaria Uno')
        self.beneficiario = crear_usuario('BEN050', RolChoices.BENEFICIARIO, nombre_completo='Ana Beneficiaria')
        self.caso = crear_caso(self.beneficiario, codigo='CASO-NOTI-001')
        self.horario_original = crear_horario(fecha=date.today() + timedelta(days=8), disponible=False)
        self.horario_nuevo = crear_horario(fecha=date.today() + timedelta(days=9), disponible=True)
        self.cita = crear_cita(self.beneficiario, self.horario_original, caso=self.caso, estado='pendiente')

    def test_reagendamiento_genera_notificacion_para_secretaria(self):
        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/reagendar/',
            {'nuevo_horario_id': self.horario_nuevo.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        cantidad = Notificacion.objects.filter(
            usuario=self.secretaria,
            tipo='reagendamiento',
        ).count()
        self.assertGreaterEqual(cantidad, 1)

    def test_notificacion_contiene_datos_de_la_cita(self):
        login_cliente(self.client, self.beneficiario.documento)
        self.client.post(
            f'/citas/{self.cita.pk}/reagendar/',
            {'nuevo_horario_id': self.horario_nuevo.pk},
            follow=True,
        )

        notificacion = Notificacion.objects.filter(
            usuario=self.secretaria,
            tipo='reagendamiento',
        ).first()

        self.assertIsNotNone(notificacion)
        self.assertIn(self.beneficiario.nombre_completo, notificacion.mensaje)
        self.assertIn(self.caso.codigo, notificacion.mensaje)


class E2E_08_AsistenciaTest(TestCase):
    def setUp(self):
        self.secretaria = crear_usuario('SEC060', RolChoices.SECRETARIA)
        self.beneficiario = crear_usuario('BEN060', RolChoices.BENEFICIARIO)
        self.caso = crear_caso(self.beneficiario, codigo='CASO-E2E-AS-1')
        self.horario = crear_horario(fecha=date.today() + timedelta(days=8), disponible=False)
        self.cita = crear_cita(self.beneficiario, self.horario, caso=self.caso, estado='confirmada')

    def test_secretaria_marca_asistencia(self):
        login_cliente(self.client, self.secretaria.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/asistencia/',
            {'accion': 'asistio'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        registro = RegistroAsistencia.objects.get(cita=self.cita)
        self.assertEqual(self.cita.estado, 'cumplida')
        self.assertTrue(registro.asistio)

    def test_secretaria_marca_inasistencia(self):
        login_cliente(self.client, self.secretaria.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/asistencia/',
            {'accion': 'no_asistio'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        registro = RegistroAsistencia.objects.get(cita=self.cita)
        self.assertEqual(self.cita.estado, 'no_asistio')
        self.assertFalse(registro.asistio)

    def test_beneficiario_no_puede_marcar_asistencia(self):
        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.post(
            f'/citas/{self.cita.pk}/asistencia/',
            {'accion': 'asistio'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'confirmada')
        self.assertFalse(RegistroAsistencia.objects.filter(cita=self.cita).exists())


class E2E_09_HistorialTest(TestCase):
    def setUp(self):
        self.secretaria = crear_usuario('SEC070', RolChoices.SECRETARIA)
        self.beneficiario = crear_usuario('BEN070', RolChoices.BENEFICIARIO)
        self.otro_beneficiario = crear_usuario('BEN071', RolChoices.BENEFICIARIO)

    def test_secretaria_puede_ver_historial(self):
        login_cliente(self.client, self.secretaria.documento)
        response = self.client.get(f'/usuarios/{self.beneficiario.pk}/historial/')
        self.assertEqual(response.status_code, 200)

    def test_beneficiario_no_puede_ver_historial_de_otro(self):
        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.get(f'/usuarios/{self.otro_beneficiario.pk}/historial/')
        self.assertIn(response.status_code, [302, 403])


class E2E_10_11_ExportarReporteTest(TestCase):
    def setUp(self):
        self.admin = crear_usuario('ADM080', RolChoices.ADMINISTRADOR)
        self.secretaria = crear_usuario('SEC080', RolChoices.SECRETARIA)
        self.beneficiario = crear_usuario('BEN080', RolChoices.BENEFICIARIO)

    def test_admin_exporta_pdf(self):
        login_cliente(self.client, self.admin.documento)
        response = self.client.get('/reportes/exportar/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.get('Content-Type', ''))

    def test_admin_exporta_excel(self):
        login_cliente(self.client, self.admin.documento)
        response = self.client.get('/reportes/exportar/excel/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response.get('Content-Type', ''))

    def test_secretaria_exporta_pdf(self):
        login_cliente(self.client, self.secretaria.documento)
        response = self.client.get('/reportes/exportar/pdf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.get('Content-Type', ''))

    def test_beneficiario_no_puede_exportar_pdf(self):
        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.get('/reportes/exportar/pdf/')
        self.assertEqual(response.status_code, 403)

    def test_beneficiario_no_puede_exportar_excel(self):
        login_cliente(self.client, self.beneficiario.documento)
        response = self.client.get('/reportes/exportar/excel/')
        self.assertEqual(response.status_code, 403)

    def test_exportar_pdf_con_filtro_sala(self):
        login_cliente(self.client, self.admin.documento)
        response = self.client.get('/reportes/exportar/pdf/?sala_juridica=civil')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/pdf', response.get('Content-Type', ''))

    def test_exportar_excel_con_filtro_fechas(self):
        login_cliente(self.client, self.admin.documento)
        fecha_inicio = (date.today() - timedelta(days=30)).isoformat()
        fecha_fin = date.today().isoformat()
        response = self.client.get(
            f'/reportes/exportar/excel/?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response.get('Content-Type', ''))


class E2E_13_ControlAccesoTest(TestCase):
    def setUp(self):
        self.estudiante = crear_usuario('EST090', RolChoices.ESTUDIANTE)
        self.profesor = crear_usuario('PRO090', RolChoices.PROFESOR)

    def test_estudiante_no_puede_exportar_pdf(self):
        login_cliente(self.client, self.estudiante.documento)
        response = self.client.get('/reportes/exportar/pdf/')
        self.assertEqual(response.status_code, 403)

    def test_profesor_no_puede_exportar_pdf(self):
        login_cliente(self.client, self.profesor.documento)
        response = self.client.get('/reportes/exportar/pdf/')
        self.assertEqual(response.status_code, 403)

    def test_acceso_sin_login_a_gestionar_citas(self):
        response = self.client.get('/gestionar-citas/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_acceso_sin_login_a_exportar_pdf(self):
        response = self.client.get('/reportes/exportar/pdf/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))
