import datetime

from django.test import TestCase

from citas.models import Caso, Cita, HorarioDisponible
from notificaciones.models import Notificacion
from notificaciones.services import crear_notificaciones_reagendamiento
from usuarios.models import Usuario


def crear_usuario(documento, rol, nombre_completo=None):
    nombre_completo = nombre_completo or f"Usuario {documento}"
    return Usuario.objects.create_user(
        documento=documento,
        correo=f"{documento}@test.com",
        nombre_completo=nombre_completo,
        password="clave1234",
        rol=rol,
    )


def crear_horario():
    fecha = datetime.date.today() + datetime.timedelta(days=5)
    return HorarioDisponible.objects.create(
        fecha=fecha,
        hora_inicio=datetime.time(10, 0),
        hora_fin=datetime.time(11, 0),
    )


def crear_caso(beneficiario):
    return Caso.objects.create(
        codigo="CASO-001",
        beneficiario=beneficiario,
        sala_juridica="civil",
        descripcion="Caso de prueba",
    )


def crear_cita(beneficiario, horario, caso=None):
    return Cita.objects.create(
        beneficiario=beneficiario,
        horario=horario,
        tipo_atencion="presencial",
        caso=caso,
    )


class NotificacionServicioTest(TestCase):

    def setUp(self):
        self.beneficiario = crear_usuario("BEN001", "beneficiario", "Juan Pérez")
        self.horario = crear_horario()
        self.caso = crear_caso(self.beneficiario)
        self.cita = crear_cita(self.beneficiario, self.horario, caso=self.caso)
        self.secretaria = crear_usuario("SEC001", "secretaria", "Ana Gómez")

    def test_crea_una_notificacion_por_destinatario(self):
        sec2 = crear_usuario("SEC002", "secretaria", "María López")
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria, sec2]
        )
        self.assertEqual(len(resultado), 2)
        self.assertEqual(Notificacion.objects.count(), 2)

    def test_retorna_lista_vacia_si_no_hay_destinatarios(self):
        resultado = crear_notificaciones_reagendamiento(self.cita, [])
        self.assertEqual(resultado, [])
        self.assertEqual(Notificacion.objects.count(), 0)

    def test_mensaje_contiene_nombre_del_beneficiario(self):
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria]
        )
        self.assertIn(self.beneficiario.nombre_completo, resultado[0].mensaje)

    def test_mensaje_contiene_codigo_del_caso(self):
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria]
        )
        self.assertIn(self.caso.codigo, resultado[0].mensaje)

    def test_mensaje_indica_sin_caso_cuando_cita_no_tiene_caso(self):
        horario2 = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=10),
            hora_inicio=datetime.time(14, 0),
            hora_fin=datetime.time(15, 0),
        )
        cita_sin_caso = crear_cita(self.beneficiario, horario2, caso=None)
        resultado = crear_notificaciones_reagendamiento(
            cita_sin_caso, [self.secretaria]
        )
        self.assertIn("sin caso asignado", resultado[0].mensaje)

    def test_mensaje_contiene_fecha_formateada(self):
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria]
        )
        fecha_esperada = self.horario.fecha.strftime("%d/%m/%Y")
        self.assertIn(fecha_esperada, resultado[0].mensaje)

    def test_mensaje_contiene_hora_formateada(self):
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria]
        )
        hora_esperada = self.horario.hora_inicio.strftime("%H:%M")
        self.assertIn(hora_esperada, resultado[0].mensaje)

    def test_tipo_notificacion_es_reagendamiento(self):
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria]
        )
        self.assertEqual(resultado[0].tipo, Notificacion.TIPO_REAGENDAMIENTO)

    def test_notificacion_leida_es_false_por_defecto(self):
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria]
        )
        self.assertFalse(resultado[0].leida)

    def test_notificacion_asignada_al_destinatario_correcto(self):
        sec2 = crear_usuario("SEC003", "secretaria", "Laura Díaz")
        resultado = crear_notificaciones_reagendamiento(
            self.cita, [self.secretaria, sec2]
        )
        usuarios_notificados = {n.usuario for n in resultado}
        self.assertIn(self.secretaria, usuarios_notificados)
        self.assertIn(sec2, usuarios_notificados)
        self.assertNotIn(self.beneficiario, usuarios_notificados)
