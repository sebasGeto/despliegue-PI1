from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from citas.models import Cita, HorarioDisponible
from usuarios.models import Usuario
from .models import LogRecordatorio
from .services import procesar_recordatorios


class RecordatoriosServicesTest(TestCase):
    def setUp(self):
        self.beneficiario = Usuario.objects.create_user(
            documento='1234567890',
            correo='beneficiario@icesi.edu.co',
            nombre_completo='Beneficiario Prueba',
            password='segura123',
            telefono='3001234567',
            rol='beneficiario',
        )

    def _crear_horario_relativo(self, delta_horas):
        fecha_hora = timezone.localtime(timezone.now()) + timedelta(hours=delta_horas)
        inicio = fecha_hora.replace(second=0, microsecond=0)
        fin = (inicio + timedelta(hours=1)).time()
        return HorarioDisponible.objects.create(
            fecha=inicio.date(),
            hora_inicio=inicio.time(),
            hora_fin=fin,
            disponible=True,
        )

    def _crear_cita(self, horario, estado='confirmada'):
        return Cita.objects.create(
            beneficiario=self.beneficiario,
            horario=horario,
            tipo_atencion='virtual',
            estado=estado,
            motivo='Prueba HU6',
        )

    @patch('recordatorios.services.send_mail', return_value=1)
    def test_recordatorio_enviado_cita_confirmada_proximas_24h(self, _mock_send_mail):
        horario = self._crear_horario_relativo(3)
        cita = self._crear_cita(horario, estado='confirmada')

        procesar_recordatorios()

        self.assertTrue(
            LogRecordatorio.objects.filter(cita=cita, estado='enviado').exists()
        )

    @patch('recordatorios.services.send_mail', return_value=1)
    def test_no_recordatorio_cita_cancelada(self, _mock_send_mail):
        horario = self._crear_horario_relativo(3)
        cita = self._crear_cita(horario, estado='cancelada')

        procesar_recordatorios()

        self.assertEqual(LogRecordatorio.objects.filter(cita=cita).count(), 0)

    @patch('recordatorios.services.send_mail', return_value=1)
    def test_no_recordatorio_cita_pasada(self, _mock_send_mail):
        horario = self._crear_horario_relativo(-24)
        cita = self._crear_cita(horario, estado='confirmada')

        procesar_recordatorios()

        self.assertEqual(LogRecordatorio.objects.filter(cita=cita).count(), 0)

    @patch('recordatorios.services._enviar_sms', side_effect=Exception('sms error'))
    @patch('recordatorios.services._enviar_email', side_effect=Exception('email error'))
    def test_log_fallido_cuando_error_en_envio(self, _mock_email, _mock_sms):
        horario = self._crear_horario_relativo(3)
        cita = self._crear_cita(horario, estado='confirmada')

        procesar_recordatorios()

        self.assertTrue(
            LogRecordatorio.objects.filter(cita=cita, estado='fallido').exists()
        )


class BitacoraRecordatoriosViewHU15Test(TestCase):

    def setUp(self):
        from django.test import Client
        self.client = Client()

        self.administrador = Usuario.objects.create_user(
            documento='ADM_HU15',
            correo='admin_hu15@test.com',
            nombre_completo='Admin HU15',
            password='clave1234',
            rol='administrador',
        )
        self.secretaria = Usuario.objects.create_user(
            documento='SEC_HU15',
            correo='sec_hu15@test.com',
            nombre_completo='Secretaria HU15',
            password='clave1234',
            rol='secretaria',
        )
        self.beneficiario = Usuario.objects.create_user(
            documento='BEN_HU15',
            correo='ben_hu15@test.com',
            nombre_completo='Beneficiario HU15',
            password='clave1234',
            rol='beneficiario',
        )
        self.estudiante = Usuario.objects.create_user(
            documento='EST_HU15',
            correo='est_hu15@test.com',
            nombre_completo='Estudiante HU15',
            password='clave1234',
            rol='estudiante',
        )
        self.profesor = Usuario.objects.create_user(
            documento='PROF_HU15',
            correo='prof_hu15@test.com',
            nombre_completo='Profesor HU15',
            password='clave1234',
            rol='profesor',
        )

        self.horario = HorarioDisponible.objects.create(
            fecha=timezone.localdate() + timedelta(days=5),
            hora_inicio=timezone.now().time().replace(microsecond=0, second=0),
            hora_fin=timezone.now().time().replace(microsecond=0, second=0),
            disponible=True,
        )
        self.cita = Cita.objects.create(
            beneficiario=self.beneficiario,
            horario=self.horario,
            tipo_atencion='presencial',
            estado='confirmada',
        )

        LogRecordatorio.objects.create(cita=self.cita, canal='email', estado='enviado', fecha_envio=timezone.now())
        LogRecordatorio.objects.create(cita=self.cita, canal='email', estado='fallido', mensaje_error='SMTP error')
        LogRecordatorio.objects.create(cita=self.cita, canal='sms', estado='enviado', fecha_envio=timezone.now())
        LogRecordatorio.objects.create(cita=self.cita, canal='sms', estado='pendiente')

    def test_administrador_accede_a_la_bitacora(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recordatorios/bitacora_recordatorios.html')

    def test_secretaria_accede_a_la_bitacora(self):
        self.client.login(documento='SEC_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/')
        self.assertEqual(response.status_code, 200)

    def test_beneficiario_no_accede_a_la_bitacora(self):
        self.client.login(documento='BEN_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/')
        self.assertRedirects(response, '/home/')

    def test_estudiante_no_accede_a_la_bitacora(self):
        self.client.login(documento='EST_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/')
        self.assertRedirects(response, '/home/')

    def test_profesor_no_accede_a_la_bitacora(self):
        self.client.login(documento='PROF_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/')
        self.assertRedirects(response, '/home/')

    def test_acceso_sin_autenticacion_redirige_a_login(self):
        response = self.client.get('/recordatorios/bitacora/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_sin_filtros_muestra_todos_los_logs(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/')
        self.assertEqual(response.context['page_obj'].paginator.count, 4)

    def test_filtro_canal_email_muestra_solo_email(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/?canal=email')
        logs = response.context['page_obj'].object_list
        self.assertEqual(len(logs), 2)
        for log in logs:
            self.assertEqual(log.canal, 'email')

    def test_filtro_canal_sms_muestra_solo_sms(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/?canal=sms')
        logs = response.context['page_obj'].object_list
        self.assertEqual(len(logs), 2)
        for log in logs:
            self.assertEqual(log.canal, 'sms')

    def test_filtro_estado_enviado_muestra_solo_enviados(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/?estado=enviado')
        logs = response.context['page_obj'].object_list
        self.assertEqual(len(logs), 2)
        for log in logs:
            self.assertEqual(log.estado, 'enviado')

    def test_filtro_estado_fallido_muestra_solo_fallidos(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/?estado=fallido')
        logs = response.context['page_obj'].object_list
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].estado, 'fallido')

    def test_combinacion_filtros_canal_y_estado(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/?canal=email&estado=enviado')
        logs = response.context['page_obj'].object_list
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].canal, 'email')
        self.assertEqual(logs[0].estado, 'enviado')

    def test_filtro_invalido_es_ignorado(self):
        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/?canal=whatsapp&estado=invalido')
        self.assertEqual(response.context['page_obj'].paginator.count, 4)

    def test_paginacion_20_por_pagina(self):
        for i in range(25):
            LogRecordatorio.objects.create(cita=self.cita, canal='email', estado='enviado')

        self.client.login(documento='ADM_HU15', password='clave1234')
        response = self.client.get('/recordatorios/bitacora/')
        self.assertEqual(len(response.context['page_obj'].object_list), 20)

        response_p2 = self.client.get('/recordatorios/bitacora/?page=2')
        self.assertGreater(len(response_p2.context['page_obj'].object_list), 0)

    def test_ultimo_recordatorio_property_devuelve_el_mas_reciente(self):
        log_mas_reciente = LogRecordatorio.objects.create(
            cita=self.cita,
            canal='sms',
            estado='enviado',
            fecha_envio=timezone.now(),
        )
        self.assertEqual(self.cita.ultimo_recordatorio.pk, log_mas_reciente.pk)

    def test_ultimo_recordatorio_property_devuelve_none_si_no_hay_logs(self):
        otro_horario = HorarioDisponible.objects.create(
            fecha=timezone.localdate() + timedelta(days=10),
            hora_inicio=self.horario.hora_inicio,
            hora_fin=self.horario.hora_fin,
            disponible=True,
        )
        cita_sin_logs = Cita.objects.create(
            beneficiario=self.beneficiario,
            horario=otro_horario,
            tipo_atencion='presencial',
            estado='confirmada',
        )
        self.assertIsNone(cita_sin_logs.ultimo_recordatorio)
