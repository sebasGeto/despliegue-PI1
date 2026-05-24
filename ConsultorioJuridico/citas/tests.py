import datetime
import threading
from datetime import time, timedelta
from django.test import TestCase, TransactionTestCase, Client, override_settings
from django.urls import reverse
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone
from usuarios.models import Usuario, RolChoices as Rol
from citas.models import Caso, HorarioDisponible, Cita, RegistroAsistencia
# Create your tests here.


#Definimos los datos que vamos a usar para desarrollar las pruebas

def crear_usuario(documento="U001", rol=Rol.BENEFICIARIO):
    return Usuario.objects.create_user(
        documento=documento,
        correo=f"{documento}@test.com",
        nombre_completo=f"Usuario {documento}",
        password="clave1234",
        rol=rol,
    )

def crear_horario(fecha=None, disponible=True):
    fecha = fecha or (datetime.date.today() + datetime.timedelta(days=5))
    return HorarioDisponible.objects.create(
        fecha=fecha,
        hora_inicio=datetime.time(10, 0),
        hora_fin=datetime.time(11, 0),
        disponible=disponible,
    )

def crear_caso(beneficiario, codigo="CASO-001"):
    return Caso.objects.create(
        codigo=codigo,
        beneficiario=beneficiario,
        sala_juridica="civil",
        descripcion="Caso de prueba",
    )

def crear_cita(beneficiario, horario, caso=None, estado="pendiente"):
    cita = Cita.objects.create(
        beneficiario=beneficiario,
        horario=horario,
        tipo_atencion="presencial",
        caso=caso,
    )
    if estado != "pendiente":
        cita.estado = estado
        cita.save()
    return cita

#Horario Disponible

class HorarioDisponibleModelTest(TestCase):

    def test_crear_horario(self):
        horario = crear_horario()
        self.assertTrue(horario.disponible)
        self.assertIsNotNone(horario.pk)

    def test_str_incluye_fecha_y_estado(self):
        horario = crear_horario()
        self.assertIn("Disponible", str(horario))

    def test_horario_unico_por_fecha_y_hora(self):
        """No se puede crear dos horarios con la misma fecha y hora de inicio."""
        fecha = datetime.date.today() + datetime.timedelta(days=7)
        HorarioDisponible.objects.create(
            fecha=fecha,
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
        )
        with self.assertRaises(Exception):
            HorarioDisponible.objects.create(
                fecha=fecha,
                hora_inicio=datetime.time(9, 0),
                hora_fin=datetime.time(10, 0),
            )

#Casos

class CasoModelTest(TestCase):

    def setUp(self):
        self.usuario = crear_usuario()

    def test_crear_caso(self):
        caso = crear_caso(self.usuario)
        self.assertEqual(caso.estado, "en_estudio")
        # En el modelo actual `estudiante_asignado` puede venir como None.
        self.assertIsNone(caso.estudiante_asignado)

        self.assertIsNone(caso.estudiante_asignado)

    def test_str_incluye_codigo_y_sala(self):
        caso = crear_caso(self.usuario, codigo="C-100")
        self.assertIn("C-100", str(caso))
        self.assertIn("Civil", str(caso))

    def test_codigo_es_unico(self):
        crear_caso(self.usuario, codigo="UNICO-01")
        with self.assertRaises(Exception):
            crear_caso(self.usuario, codigo="UNICO-01")

#Estado de las citas

class CitaModelTest(TestCase):

    def setUp(self):
        self.usuario = crear_usuario()
        self.horario = crear_horario()
        self.caso = crear_caso(self.usuario)
        self.cita = crear_cita(self.usuario, self.horario, self.caso)

    def test_cita_estado_inicial_es_pendiente(self):
        self.assertEqual(self.cita.estado, "pendiente")

    def test_puede_confirmar_desde_pendiente(self):
        self.assertTrue(self.cita.puede_confirmar())

    def test_no_puede_confirmar_desde_confirmada(self):
        self.cita.cambiar_estado("confirmada")
        self.assertFalse(self.cita.puede_confirmar())

    def test_puede_cancelar_desde_pendiente(self):
        self.assertTrue(self.cita.puede_cancelar())

    def test_puede_cancelar_desde_confirmada(self):
        self.cita.cambiar_estado("confirmada")
        self.assertTrue(self.cita.puede_cancelar())

    def test_no_puede_cancelar_desde_cumplida(self):
        self.cita.estado = "cumplida"
        self.cita.save()
        self.assertFalse(self.cita.puede_cancelar())

    def test_transicion_valida_pendiente_a_confirmada(self):
        self.cita.cambiar_estado("confirmada")
        self.assertEqual(self.cita.estado, "confirmada")

    def test_transicion_valida_confirmada_a_cumplida(self):
        self.cita.cambiar_estado("confirmada")
        self.cita.cambiar_estado("cumplida")
        self.assertEqual(self.cita.estado, "cumplida")

    def test_transicion_invalida_lanza_error(self):
        """No se puede pasar de 'pendiente' directamente a 'cumplida'."""
        with self.assertRaises(ValidationError):
            self.cita.cambiar_estado("cumplida")

    def test_cancelar_libera_horario(self):
        """Al cancelar una cita, el horario vuelve a estar disponible."""
        self.horario.disponible = False
        self.horario.save()
        self.cita.cambiar_estado("cancelada")
        self.horario.refresh_from_db()
        self.assertTrue(self.horario.disponible)

    def test_confirmar_registra_fecha_confirmacion(self):
        self.cita.cambiar_estado("confirmada")
        self.assertIsNotNone(self.cita.fecha_confirmacion)

    def test_cancelar_registra_fecha_cancelacion(self):
        self.cita.cambiar_estado("cancelada")
        self.assertIsNotNone(self.cita.fecha_cancelacion)

    def test_str_incluye_estado(self):
        self.assertIn("Pendiente", str(self.cita))

#Registro de asistencia

class RegistroAsistenciaModelTest(TestCase):

    def setUp(self):
        self.usuario = crear_usuario()
        self.admin = crear_usuario(documento="ADMIN", rol=Rol.ADMINISTRADOR)
        self.horario = crear_horario()
        self.cita = crear_cita(self.usuario, self.horario)
        self.cita.cambiar_estado("confirmada")

    def test_crear_registro_asistencia(self):
        registro = RegistroAsistencia.objects.create(
            cita=self.cita,
            asistio=True,
            registrado_por=self.admin,
        )
        self.assertTrue(registro.asistio)

    def test_str_incluye_estado_asistencia(self):
        registro = RegistroAsistencia.objects.create(
            cita=self.cita,
            asistio=False,
            registrado_por=self.admin,
        )
        self.assertIn("No asistió", str(registro))

    def test_registro_es_unico_por_cita(self):
        """No puede haber dos registros de asistencia para la misma cita."""
        RegistroAsistencia.objects.create(
            cita=self.cita, asistio=True, registrado_por=self.admin,
        )
        with self.assertRaises(Exception):
            RegistroAsistencia.objects.create(
                cita=self.cita, asistio=False, registrado_por=self.admin,
            )

#Vistas de dashboard

class DashboardViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.client.login(documento="U001", password="clave1234")

    def test_home_accesible_para_usuario_autenticado(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_home_redirige_si_no_autenticado(self):
        self.client.logout()
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_home_muestra_proxima_cita(self):
        """El contexto del home incluye la próxima cita activa del usuario."""
        horario = crear_horario()
        caso = crear_caso(self.usuario)
        crear_cita(self.usuario, horario, caso)
        response = self.client.get(reverse("home"))
        self.assertIsNotNone(response.context["proxima_cita"])

    def test_home_sin_citas_proxima_cita_es_none(self):
        response = self.client.get(reverse("home"))
        self.assertIsNone(response.context["proxima_cita"])

    def test_home_incluye_casos_del_usuario(self):
        crear_caso(self.usuario, codigo="C-HOME-01")
        crear_caso(self.usuario, codigo="C-HOME-02")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["casos"].count(), 2)

#Gestion de citas

class GestionarCitasViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.admin = crear_usuario(documento="SEC01", rol=Rol.SECRETARIA)
        self.horario = crear_horario()
        self.caso = crear_caso(self.usuario)
        self.cita = crear_cita(self.usuario, self.horario, self.caso)
        self.client.login(documento="U001", password="clave1234")

    def test_vista_accesible(self):
        response = self.client.get(reverse("gestionar_citas"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "citas/gestionar_citas.html")

    def test_beneficiario_solo_ve_sus_citas(self):
        """El beneficiario solo debe ver sus propias citas."""
        otro = crear_usuario(documento="OTRO")
        otro_horario = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=6),
            hora_inicio=datetime.time(14, 0),
            hora_fin=datetime.time(15, 0),
        )
        crear_cita(otro, otro_horario)
        response = self.client.get(reverse("gestionar_citas"))
        for cita in response.context["historial_citas"]:
            self.assertEqual(cita.beneficiario, self.usuario)

    def test_admin_ve_todas_las_citas(self):
        """La secretaria/admin debe ver todas las citas en el historial."""
        self.client.login(documento="SEC01", password="clave1234")
        response = self.client.get(reverse("gestionar_citas"))
        self.assertTrue(response.context["es_admin"])

    def test_admin_filtro_estado_filtra_citas_por_estado(self):
        """El administrador puede filtrar el historial de citas por estado."""
        self.client.login(documento="SEC01", password="clave1234")
        otra_hora = crear_horario(fecha=datetime.date.today() + datetime.timedelta(days=6))
        crear_cita(self.usuario, otra_hora, self.caso, estado="confirmada")
        crear_cita(self.usuario, crear_horario(fecha=datetime.date.today() + datetime.timedelta(days=7)), self.caso, estado="cancelada")

        response = self.client.get(reverse("gestionar_citas") + "?estado=confirmada")
        historial = response.context["historial_citas"]
        self.assertTrue(all(cita.estado == "confirmada" for cita in historial))
        self.assertEqual(len(historial), 1)

    def test_admin_filtro_beneficiario_filtra_correctamente(self):
        """El administrador puede filtrar el historial por beneficiario."""
        otro_beneficiario = crear_usuario(documento="U002")
        otro_caso = crear_caso(otro_beneficiario, codigo="CASO-002")
        otro_horario = crear_horario(fecha=datetime.date.today() + datetime.timedelta(days=6))
        crear_cita(otro_beneficiario, otro_horario, otro_caso, estado="confirmada")

        self.client.login(documento="SEC01", password="clave1234")
        response = self.client.get(reverse("gestionar_citas") + f"?beneficiario={otro_beneficiario.pk}")
        historial = response.context["historial_citas"]
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0].beneficiario, otro_beneficiario)

    def test_detalle_cita_por_query_param(self):
        """Si se pasa ?cita_id=N, la vista retorna esa cita como seleccionada."""
        response = self.client.get(
            reverse("gestionar_citas") + f"?cita_id={self.cita.pk}"
        )
        self.assertEqual(response.context["cita_seleccionada"], self.cita)

    def test_usuario_con_una_cita_muestra_historial(self):
        """Usuario con una cita debe ver su cita en el historial."""
        response = self.client.get(reverse("gestionar_citas"))
        historial = response.context["historial_citas"]
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0], self.cita)

    def test_usuario_sin_citas_muestra_mensaje_vacio(self):
        """Usuario sin citas debe ver mensaje de no tener historial."""
        # Crear un usuario nuevo sin citas
        usuario_sin_citas = crear_usuario(documento="SIN01")
        self.client.login(documento="SIN01", password="clave1234")
        response = self.client.get(reverse("gestionar_citas"))
        historial = response.context["historial_citas"]
        self.assertEqual(len(historial), 0)
        # Verificar que la plantilla renderiza el mensaje
        self.assertContains(response, "No tiene historial de citas.")

    def test_usuario_con_multiples_citas_muestra_todas(self):
        """Usuario con múltiples citas debe ver todas en el historial."""
        # Crear otra cita para el mismo usuario
        otro_horario = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=7),
            hora_inicio=datetime.time(16, 0),
            hora_fin=datetime.time(17, 0),
        )
        otra_cita = crear_cita(self.usuario, otro_horario, self.caso)
        response = self.client.get(reverse("gestionar_citas"))
        historial = response.context["historial_citas"]
        self.assertEqual(len(historial), 2)
        citas_ids = [cita.pk for cita in historial]
        self.assertIn(self.cita.pk, citas_ids)
        self.assertIn(otra_cita.pk, citas_ids)


class ApiCitasEstadoActualTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.beneficiario = crear_usuario()
        self.estudiante = crear_usuario(documento="EST01", rol=Rol.ESTUDIANTE)
        self.admin = crear_usuario(documento="ADM01", rol=Rol.ADMINISTRADOR)
        self.profesor = crear_usuario(documento="PROF01", rol=Rol.PROFESOR)
        self.horario = crear_horario()
        self.caso = crear_caso(self.beneficiario)
        self.caso.estudiante_asignado = self.estudiante
        self.caso.save()
        self.cita = crear_cita(self.beneficiario, self.horario, self.caso)

    def test_api_citas_beneficiario_retiene_sus_citas(self):
        self.client.login(documento="U001", password="clave1234")
        response = self.client.get(reverse("api_citas_estado_actual"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["proxima_cita"]["caso_codigo"], self.caso.codigo)
        self.assertEqual(len(data["historial_citas"]), 1)

    def test_api_citas_filtra_por_estado(self):
        self.cita.estado = "confirmada"
        self.cita.save()
        otra_horario = crear_horario(fecha=datetime.date.today() + datetime.timedelta(days=6))
        crear_cita(self.beneficiario, otra_horario, self.caso, estado="pendiente")

        self.client.login(documento="U001", password="clave1234")
        response = self.client.get(reverse("api_citas_estado_actual") + "?estado=confirmada")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["historial_citas"]), 1)
        self.assertEqual(data["historial_citas"][0]["estado"], "confirmada")

    def test_api_citas_estudiante_retiene_citas_de_sus_casos(self):
        self.client.login(documento="EST01", password="clave1234")
        response = self.client.get(reverse("api_citas_estado_actual"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["historial_citas"]), 1)
        self.assertEqual(data["historial_citas"][0]["caso_codigo"], self.caso.codigo)

    def test_api_citas_admin_ve_todas_las_citas(self):
        self.client.login(documento="ADM01", password="clave1234")
        response = self.client.get(reverse("api_citas_estado_actual"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["historial_citas"]), 1)

    def test_api_citas_profesor_retorna_vacio_por_falta_de_relacion(self):
        self.client.login(documento="PROF01", password="clave1234")
        response = self.client.get(reverse("api_citas_estado_actual"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["historial_citas"]), 0)

#Cancelacion de citas

class CancelarCitaViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.horario = crear_horario()
        self.caso = crear_caso(self.usuario)
        self.cita = crear_cita(self.usuario, self.horario, self.caso)
        self.client.login(documento="U001", password="clave1234")

    def test_cancelar_cita_pendiente(self):
        response = self.client.post(
            reverse("cancelar_cita", args=[self.cita.pk])
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "cancelada")
        self.assertRedirects(response, reverse("gestionar_citas"))

    def test_cancelar_cita_de_otro_usuario_retorna_404(self):
        otro = crear_usuario(documento="OTRO2")
        otro_horario = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=8),
            hora_inicio=datetime.time(11, 0),
            hora_fin=datetime.time(12, 0),
        )
        cita_ajena = crear_cita(otro, otro_horario)
        response = self.client.post(
            reverse("cancelar_cita", args=[cita_ajena.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_cancelar_cita_cumplida_muestra_error(self):
        """No se puede cancelar una cita ya cumplida; debe mostrar error."""
        self.cita.estado = "cumplida"
        self.cita.save()
        self.client.post(reverse("cancelar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        # El estado no debe haber cambiado
        self.assertEqual(self.cita.estado, "cumplida")


#Posponer citas (DEPRECADO - reemplazado por reagendar_cita_view)
class PosponerCitaViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.horario = crear_horario()
        self.caso = crear_caso(self.usuario)
        self.cita = crear_cita(self.usuario, self.horario, self.caso)
        self.client.login(documento="U001", password="clave1234")

    def test_posponer_no_modifica_cita(self):
        """La vista deprecada no debe modificar el estado de la cita."""
        self.client.post(reverse("posponer_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "pendiente")

    def test_posponer_redirige_a_gestionar_citas(self):
        """La vista deprecada redirige a gestionar_citas."""
        response = self.client.post(
            reverse("posponer_cita", args=[self.cita.pk])
        )
        self.assertRedirects(response, reverse("gestionar_citas"))


#Confirmacion de citas
class ConfirmarCitaViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.horario = crear_horario()
        self.caso = crear_caso(self.usuario)
        self.cita = crear_cita(self.usuario, self.horario, self.caso)
        self.client.login(documento="U001", password="clave1234")

    def test_confirmar_cita_pendiente(self):
        self.client.post(reverse("confirmar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "confirmada")

    def test_confirmar_redirige_a_gestionar_citas(self):
        response = self.client.post(
            reverse("confirmar_cita", args=[self.cita.pk])
        )
        self.assertRedirects(response, reverse("gestionar_citas"))

    def test_confirmar_cita_ya_confirmada_muestra_error(self):
        """Intentar confirmar una cita ya confirmada no debe cambiar su estado."""
        self.cita.cambiar_estado("confirmada")
        self.client.post(reverse("confirmar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        # Sigue confirmada, no se rompe
        self.assertEqual(self.cita.estado, "confirmada")

#Gestionar casos y agendamiento de citas

class GestionarCasosViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.caso = crear_caso(self.usuario)
        self.horario = crear_horario()
        self.client.login(documento="U001", password="clave1234")

    def test_vista_gestionar_casos_accesible(self):
        response = self.client.get(reverse("gestionar_casos"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "citas/gestionar_casos.html")

    def test_casos_del_usuario_en_contexto(self):
        response = self.client.get(reverse("gestionar_casos"))
        self.assertIn(self.caso, response.context["casos"])

    def test_caso_seleccionado_por_query_param(self):
        response = self.client.get(
            reverse("gestionar_casos") + f"?caso_id={self.caso.pk}"
        )
        self.assertEqual(response.context["caso_seleccionado"], self.caso)

    def test_horarios_disponibles_en_contexto(self):
        response = self.client.get(reverse("gestionar_casos"))
        self.assertIn(self.horario, response.context["horarios_disponibles"])

    def test_admin_ve_todos_los_casos(self):
        otro_beneficiario = crear_usuario(documento="U002")
        crear_caso(otro_beneficiario, codigo="C-OTRO")
        admin = crear_usuario(documento="SEC01", rol=Rol.SECRETARIA)
        self.client.logout()
        self.assertTrue(self.client.login(documento="SEC01", password="clave1234"))
        response = self.client.get(reverse("gestionar_casos"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["casos"].count(), 2)

    def test_estudiante_ve_solo_sus_casos_asignados(self):
        estudiante = crear_usuario(documento="EST02", rol=Rol.ESTUDIANTE)
        beneficiario = crear_usuario(documento="U002")
        caso_asignado = Caso.objects.create(
            codigo="C-EST01",
            beneficiario=beneficiario,
            sala_juridica="civil",
            descripcion="Caso asignado al estudiante",
            estudiante_asignado=estudiante,
        )
        self.client.login(documento="EST02", password="clave1234")
        response = self.client.get(reverse("gestionar_casos"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(caso_asignado, response.context["casos"])
        self.assertEqual(response.context["casos"].count(), 1)

    def test_agendar_cita_crea_cita(self):
        """POST a agendar_cita debe crear una nueva cita."""
        response = self.client.post(reverse("agendar_cita"), {
            "caso_id": self.caso.pk,
            "fecha": self.horario.fecha.strftime("%Y-%m-%d"),
            "hora": "10:00",
            "tipo_atencion": "presencial",
        })
        self.assertTrue(
            Cita.objects.filter(caso=self.caso, beneficiario=self.usuario).exists()
        )

    def test_agendar_cita_marca_horario_no_disponible(self):
        """Después de agendar, el horario debe quedar no disponible."""
        self.client.post(reverse("agendar_cita"), {
            "caso_id": self.caso.pk,
            "fecha": self.horario.fecha.strftime("%Y-%m-%d"),
            "hora": "10:00",
            "tipo_atencion": "presencial",
        })
        self.horario.refresh_from_db()
        self.assertFalse(self.horario.disponible)

    def test_agendar_cita_redirige_a_gestionar_citas(self):
        response = self.client.post(reverse("agendar_cita"), {
            "caso_id": self.caso.pk,
            "fecha": self.horario.fecha.strftime("%Y-%m-%d"),
            "hora": "10:00",
            "tipo_atencion": "presencial",
        })
        self.assertRedirects(response, reverse("gestionar_citas"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_agendar_cita_envia_correo_recordatorio(self):
        self.client.post(reverse("agendar_cita"), {
            "caso_id": self.caso.pk,
            "fecha": self.horario.fecha.strftime("%Y-%m-%d"),
            "hora": "10:00",
            "tipo_atencion": "presencial",
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.usuario.correo])
        self.assertIn("Recordatorio", mail.outbox[0].subject)

#No duplicar citas por casos
class ValidacionCitaDuplicadaTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.caso = crear_caso(self.usuario)
        self.horario1 = crear_horario()
        self.horario2 = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=10),
            hora_inicio=datetime.time(15, 0),
            hora_fin=datetime.time(16, 0),
        )
        self.client.login(documento="U001", password="clave1234")
        # Agendar primera cita
        self.client.post(reverse("agendar_cita"), {
            "caso_id": self.caso.pk,
            "fecha": self.horario1.fecha.strftime("%Y-%m-%d"),
            "hora": "10:00",
            "tipo_atencion": "presencial",
        })

    def test_no_se_puede_agendar_segunda_cita_activa_para_mismo_caso(self):
        """Si el caso ya tiene una cita activa, no debe crearse otra."""
        citas_antes = Cita.objects.filter(caso=self.caso).count()
        self.client.post(reverse("agendar_cita"), {
            "caso_id": self.caso.pk,
            "fecha": self.horario2.fecha.strftime("%Y-%m-%d"),
            "hora": "15:00",
            "tipo_atencion": "virtual",
        })
        citas_despues = Cita.objects.filter(caso=self.caso).count()
        # Sigue siendo 1
        self.assertEqual(citas_antes, citas_despues)

    def test_despues_de_cancelar_si_se_puede_agendar(self):
        """Tras cancelar la cita activa, debe permitirse agendar una nueva."""
        cita_activa = Cita.objects.filter(
            caso=self.caso, estado__in=["pendiente", "confirmada"]
        ).first()
        self.client.post(reverse("cancelar_cita", args=[cita_activa.pk]))

        self.client.post(reverse("agendar_cita"), {
            "caso_id": self.caso.pk,
            "fecha": self.horario2.fecha.strftime("%Y-%m-%d"),
            "hora": "15:00",
            "tipo_atencion": "virtual",
        })
        citas_activas = Cita.objects.filter(
            caso=self.caso, estado__in=["pendiente", "confirmada"]
        ).count()
        self.assertEqual(citas_activas, 1)

#Marcar asistencia

class MarcarAsistenciaViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuario = crear_usuario()
        self.secretaria = crear_usuario(documento="SEC02", rol=Rol.SECRETARIA)
        self.horario = crear_horario()
        self.caso = crear_caso(self.usuario)
        self.cita = crear_cita(self.usuario, self.horario, self.caso)
        self.cita.cambiar_estado("confirmada")

    def test_secretaria_puede_marcar_asistencia(self):
        self.client.login(documento="SEC02", password="clave1234")
        self.client.post(
            reverse("marcar_asistencia", args=[self.cita.pk]),
            {"accion": "asistio"},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "cumplida")

    def test_secretaria_puede_marcar_inasistencia(self):
        self.client.login(documento="SEC02", password="clave1234")
        self.client.post(
            reverse("marcar_asistencia", args=[self.cita.pk]),
            {"accion": "no_asistio"},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "no_asistio")

    def test_marcar_asistencia_crea_registro(self):
        self.client.login(documento="SEC02", password="clave1234")
        self.client.post(
            reverse("marcar_asistencia", args=[self.cita.pk]),
            {"accion": "asistio"},
        )
        self.assertTrue(
            RegistroAsistencia.objects.filter(cita=self.cita).exists()
        )

    def test_beneficiario_no_puede_marcar_asistencia(self):
        """Un beneficiario no debe tener acceso a marcar asistencia."""
        self.client.login(documento="U001", password="clave1234")
        response = self.client.post(
            reverse("marcar_asistencia", args=[self.cita.pk]),
            {"accion": "asistio"},
        )
        # Redirige sin cambiar el estado (sin permisos)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "confirmada")

    def test_no_se_puede_marcar_asistencia_en_cita_pendiente(self):
        """Solo citas confirmadas aceptan registro de asistencia."""
        self.client.login(documento="SEC02", password="clave1234")
        horario2 = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=12),
            hora_inicio=datetime.time(8, 0),
            hora_fin=datetime.time(9, 0),
        )
        cita_pendiente = crear_cita(self.usuario, horario2, self.caso)
        self.client.post(
            reverse("marcar_asistencia", args=[cita_pendiente.pk]),
            {"accion": "asistio"},
        )
        cita_pendiente.refresh_from_db()
        # Debe seguir pendiente, no cambió
        self.assertEqual(cita_pendiente.estado, "pendiente")


#HU5 - Cancelacion de citas (Sprint 2)

class CancelarCitaHU5Test(TestCase):

    def setUp(self):
        self.client = Client()
        self.beneficiario = crear_usuario(documento="BEN001", rol=Rol.BENEFICIARIO)
        self.secretaria = crear_usuario(documento="SEC10", rol=Rol.SECRETARIA)
        self.administrador = crear_usuario(documento="ADM10", rol=Rol.ADMINISTRADOR)
        self.profesor = crear_usuario(documento="PROF10", rol=Rol.PROFESOR)
        self.estudiante = crear_usuario(documento="EST10", rol=Rol.ESTUDIANTE)
        self.horario = crear_horario()
        self.caso = crear_caso(self.beneficiario)
        self.cita = crear_cita(self.beneficiario, self.horario, self.caso)

    def test_motivo_se_guarda_al_cancelar(self):
        """El motivo enviado en el POST se persiste en motivo_cancelacion."""
        self.client.login(documento="BEN001", password="clave1234")
        self.client.post(
            reverse("cancelar_cita", args=[self.cita.pk]),
            {"motivo": "No me sirve el horario"},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.motivo_cancelacion, "No me sirve el horario")

    def test_cancelada_por_registra_al_usuario(self):
        """Al cancelar, se registra en cancelada_por el usuario que ejecuto la accion."""
        self.client.login(documento="BEN001", password="clave1234")
        self.client.post(reverse("cancelar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.cancelada_por, self.beneficiario)

    def test_secretaria_puede_cancelar_cita_ajena(self):
        """La secretaria puede cancelar citas de cualquier beneficiario."""
        self.client.login(documento="SEC10", password="clave1234")
        self.client.post(reverse("cancelar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "cancelada")
        self.assertEqual(self.cita.cancelada_por, self.secretaria)

    def test_administrador_puede_cancelar_cita_ajena(self):
        """El administrador puede cancelar citas de cualquier beneficiario."""
        self.client.login(documento="ADM10", password="clave1234")
        self.client.post(reverse("cancelar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "cancelada")
        self.assertEqual(self.cita.cancelada_por, self.administrador)

    def test_profesor_no_puede_cancelar_cita(self):
        """Un profesor no tiene permiso para cancelar citas."""
        self.client.login(documento="PROF10", password="clave1234")
        self.client.post(reverse("cancelar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "pendiente")

    def test_estudiante_no_puede_cancelar_cita(self):
        """Un estudiante no tiene permiso para cancelar citas."""
        self.client.login(documento="EST10", password="clave1234")
        self.client.post(reverse("cancelar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "pendiente")

    def test_no_se_puede_cancelar_cita_pasada(self):
        """No debe permitirse cancelar una cita cuya fecha y hora ya pasaron."""
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=1),
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
        )
        cita_pasada = crear_cita(self.beneficiario, horario_pasado, self.caso)
        self.client.login(documento="BEN001", password="clave1234")
        self.client.post(reverse("cancelar_cita", args=[cita_pasada.pk]))
        cita_pasada.refresh_from_db()
        self.assertEqual(cita_pasada.estado, "pendiente")

    def test_puede_cancelar_es_false_si_cita_es_pasada(self):
        """El metodo puede_cancelar() debe retornar False para citas pasadas."""
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=2),
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
        )
        cita_pasada = crear_cita(self.beneficiario, horario_pasado, self.caso)
        self.assertFalse(cita_pasada.puede_cancelar())

    def test_es_pasada_retorna_true_para_cita_vencida(self):
        """es_pasada() retorna True si la fecha+hora ya paso."""
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=1),
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
        )
        cita_pasada = crear_cita(self.beneficiario, horario_pasado, self.caso)
        self.assertTrue(cita_pasada.es_pasada())

    def test_es_pasada_retorna_false_para_cita_futura(self):
        """es_pasada() retorna False si la fecha+hora es futura."""
        self.assertFalse(self.cita.es_pasada())

    def test_cancelacion_sin_motivo_guarda_string_vacio(self):
        """Si no se envia motivo, se guarda un string vacio (no None)."""
        self.client.login(documento="BEN001", password="clave1234")
        self.client.post(reverse("cancelar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.motivo_cancelacion, "")

    #HU4 - Reagendamiento de citas (Sprint 2)

class ReagendarCitaHU4Test(TestCase):

    def setUp(self):
        self.client = Client()
        self.beneficiario = crear_usuario(documento="BEN200", rol=Rol.BENEFICIARIO)
        self.secretaria = crear_usuario(documento="SEC200", rol=Rol.SECRETARIA)
        self.administrador = crear_usuario(documento="ADM200", rol=Rol.ADMINISTRADOR)
        self.profesor = crear_usuario(documento="PROF200", rol=Rol.PROFESOR)
        self.estudiante = crear_usuario(documento="EST200", rol=Rol.ESTUDIANTE)
        self.horario_actual = crear_horario()
        self.caso = crear_caso(self.beneficiario)
        self.cita = crear_cita(self.beneficiario, self.horario_actual, self.caso)
        self.horario_nuevo = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=10),
            hora_inicio=datetime.time(14, 0),
            hora_fin=datetime.time(15, 0),
        )
        # Marcar el horario actual como ocupado (consistente con flujo real)
        self.horario_actual.disponible = False
        self.horario_actual.save()

    def test_reagendamiento_exitoso_beneficiario(self):
        """El beneficiario puede reagendar su propia cita."""
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_nuevo)

    def test_reagendamiento_libera_horario_anterior(self):
        """Al reagendar, el horario viejo queda disponible."""
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.horario_actual.refresh_from_db()
        self.assertTrue(self.horario_actual.disponible)

    def test_reagendamiento_ocupa_horario_nuevo(self):
        """Al reagendar, el horario nuevo queda ocupado."""
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.horario_nuevo.refresh_from_db()
        self.assertFalse(self.horario_nuevo.disponible)

    def test_reagendamiento_registra_horario_anterior(self):
        """El horario_anterior queda guardado para trazabilidad."""
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario_anterior, self.horario_actual)

    def test_reagendamiento_registra_quien_lo_hizo(self):
        """reagendada_por queda con el usuario que ejecuto la accion."""
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.reagendada_por, self.beneficiario)

    def test_reagendamiento_registra_fecha(self):
        """fecha_reagendamiento queda con la marca temporal."""
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertIsNotNone(self.cita.fecha_reagendamiento)

    def test_secretaria_puede_reagendar_cita_ajena(self):
        """La secretaria puede reagendar citas de cualquier beneficiario."""
        self.client.login(documento="SEC200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_nuevo)
        self.assertEqual(self.cita.reagendada_por, self.secretaria)

    def test_administrador_puede_reagendar_cita_ajena(self):
        """El administrador puede reagendar citas de cualquier beneficiario."""
        self.client.login(documento="ADM200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_nuevo)

    def test_profesor_no_puede_reagendar(self):
        """Un profesor no tiene permiso para reagendar citas."""
        self.client.login(documento="PROF200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_actual)

    def test_estudiante_no_puede_reagendar(self):
        """Un estudiante no tiene permiso para reagendar citas."""
        self.client.login(documento="EST200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_actual)

    def test_no_se_puede_reagendar_a_horario_ocupado(self):
        """No se puede reagendar a un horario que ya esta ocupado."""
        self.horario_nuevo.disponible = False
        self.horario_nuevo.save()
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_actual)

    def test_no_se_puede_reagendar_a_horario_pasado(self):
        """No se puede reagendar a un horario cuya fecha y hora ya pasaron."""
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=2),
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
        )
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": horario_pasado.pk},
        )
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_actual)

    def test_no_se_puede_reagendar_cita_pasada(self):
        """No se puede reagendar una cita cuya fecha ya paso."""
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=1),
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
        )
        cita_pasada = crear_cita(self.beneficiario, horario_pasado, self.caso)
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[cita_pasada.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        cita_pasada.refresh_from_db()
        self.assertEqual(cita_pasada.horario, horario_pasado)

    def test_no_se_puede_reagendar_cita_cancelada(self):
        """No se puede reagendar una cita cancelada."""
        self.cita.cambiar_estado('cancelada')
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(
            reverse("reagendar_cita", args=[self.cita.pk]),
            {"nuevo_horario_id": self.horario_nuevo.pk},
        )
        self.cita.refresh_from_db()
        self.assertNotEqual(self.cita.horario, self.horario_nuevo)

    def test_reagendar_sin_horario_no_modifica_cita(self):
        """Si no se envia nuevo_horario_id, la cita queda sin cambios."""
        self.client.login(documento="BEN200", password="clave1234")
        self.client.post(reverse("reagendar_cita", args=[self.cita.pk]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.horario, self.horario_actual)

    def test_puede_reagendar_es_true_para_cita_pendiente_futura(self):
        """puede_reagendar() retorna True para citas pendientes futuras."""
        self.assertTrue(self.cita.puede_reagendar())

    def test_puede_reagendar_es_false_para_cita_pasada(self):
        """puede_reagendar() retorna False para citas pasadas."""
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=2),
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
        )
        cita_pasada = crear_cita(self.beneficiario, horario_pasado, self.caso)
        self.assertFalse(cita_pasada.puede_reagendar())


# HU14 - Detección visual de citas pendientes que requieren atención

class HU14RequiereAtencionTest(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(documento="BEN-HU14")
        self.caso = crear_caso(self.usuario, codigo="CASO-HU14")

    def test_pendiente_no_requiere_atencion_si_es_futura(self):
        horario_futuro = HorarioDisponible.objects.create(
            fecha=datetime.date.today() + datetime.timedelta(days=1),
            hora_inicio=datetime.time(10, 0),
            hora_fin=datetime.time(11, 0),
        )
        cita = crear_cita(self.usuario, horario_futuro, self.caso, estado="pendiente")
        self.assertFalse(cita.requiere_atencion_automatico(tolerancia_minutos=15))

    def test_pendiente_requiere_atencion_si_ya_vencio(self):
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=1),
            hora_inicio=datetime.time(10, 0),
            hora_fin=datetime.time(11, 0),
        )
        cita = crear_cita(self.usuario, horario_pasado, self.caso, estado="pendiente")
        self.assertTrue(cita.requiere_atencion_automatico(tolerancia_minutos=15))

    def test_no_aplica_si_cita_no_esta_pendiente(self):
        horario_pasado = HorarioDisponible.objects.create(
            fecha=datetime.date.today() - datetime.timedelta(days=1),
            hora_inicio=datetime.time(10, 0),
            hora_fin=datetime.time(11, 0),
        )
        cita = crear_cita(self.usuario, horario_pasado, self.caso, estado="confirmada")
        self.assertFalse(cita.requiere_atencion_automatico(tolerancia_minutos=15))

class ValidacionDisponibilidadHU10Test(TestCase):
    """Pruebas estándar para HU10 - Validación automática de disponibilidad."""

    def setUp(self):
        self.beneficiario = Usuario.objects.create_user(
            documento='1111111111',
            password='Password123',
            nombre_completo='Beneficiario HU10',
            correo='hu10@test.com',
            telefono='3001112233',
            direccion='Calle 1',
            rol='beneficiario',
        )
        self.caso = Caso.objects.create(
            codigo='CASO-HU10-001',
            beneficiario=self.beneficiario,
            sala_juridica='civil',
            descripcion='Caso para HU10',
        )
        # Horario futuro disponible
        fecha_futura = timezone.localdate() + timedelta(days=7)
        self.horario_disponible = HorarioDisponible.objects.create(
            fecha=fecha_futura,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            disponible=True,
        )
        self.client.login(documento='1111111111', password='Password123')

    def test_agendar_horario_disponible_exitoso(self):
        """Caso feliz: agendar en horario libre crea la cita y marca el horario ocupado."""
        response = self.client.post('/agendar-cita/', {
            'caso_id': self.caso.pk,
            'fecha': self.horario_disponible.fecha.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'tipo_atencion': 'presencial',
        })

        self.assertEqual(Cita.objects.filter(caso=self.caso).count(), 1)
        self.horario_disponible.refresh_from_db()
        self.assertFalse(self.horario_disponible.disponible)

    def test_agendar_horario_ocupado_falla(self):
        """No se puede agendar sobre un horario marcado como no disponible."""
        self.horario_disponible.disponible = False
        self.horario_disponible.save()

        response = self.client.post('/agendar-cita/', {
            'caso_id': self.caso.pk,
            'fecha': self.horario_disponible.fecha.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'tipo_atencion': 'presencial',
        })

        self.assertEqual(Cita.objects.filter(caso=self.caso).count(), 0)

    def test_agendar_horario_pasado_falla(self):
        """No se puede agendar en un horario con fecha/hora pasada."""
        fecha_pasada = timezone.localdate() - timedelta(days=1)
        horario_pasado = HorarioDisponible.objects.create(
            fecha=fecha_pasada,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            disponible=True,
        )

        response = self.client.post('/agendar-cita/', {
            'caso_id': self.caso.pk,
            'fecha': horario_pasado.fecha.strftime('%Y-%m-%d'),
            'hora': '10:00',
            'tipo_atencion': 'presencial',
        })

        self.assertEqual(Cita.objects.filter(caso=self.caso).count(), 0)

    def test_agendar_doble_cita_mismo_caso_falla(self):
        """Un caso con cita activa no puede tener otra cita activa simultánea."""
        # Crear primera cita activa
        Cita.objects.create(
            beneficiario=self.beneficiario,
            caso=self.caso,
            horario=self.horario_disponible,
            tipo_atencion='presencial',
            estado='pendiente',
        )

        # Intentar crear segunda cita en otro horario
        otro_horario = HorarioDisponible.objects.create(
            fecha=self.horario_disponible.fecha,
            hora_inicio=time(11, 0),
            hora_fin=time(12, 0),
            disponible=True,
        )

        response = self.client.post('/agendar-cita/', {
            'caso_id': self.caso.pk,
            'fecha': otro_horario.fecha.strftime('%Y-%m-%d'),
            'hora': '11:00',
            'tipo_atencion': 'presencial',
        })

        self.assertEqual(Cita.objects.filter(caso=self.caso).count(), 1)


class ValidacionDisponibilidadConcurrenciaHU10Test(TransactionTestCase):

    def setUp(self):
        self.beneficiario_a = Usuario.objects.create_user(
            documento='2222222222',
            password='Password123',
            nombre_completo='Beneficiario A',
            correo='a@test.com',
            telefono='3001112233',
            direccion='Calle A',
            rol='beneficiario',
        )
        self.beneficiario_b = Usuario.objects.create_user(
            documento='3333333333',
            password='Password123',
            nombre_completo='Beneficiario B',
            correo='b@test.com',
            telefono='3004445566',
            direccion='Calle B',
            rol='beneficiario',
        )
        self.caso_a = Caso.objects.create(
            codigo='CASO-A',
            beneficiario=self.beneficiario_a,
            sala_juridica='civil',
            descripcion='Caso A',
        )
        self.caso_b = Caso.objects.create(
            codigo='CASO-B',
            beneficiario=self.beneficiario_b,
            sala_juridica='civil',
            descripcion='Caso B',
        )
        fecha_futura = timezone.localdate() + timedelta(days=7)
        self.horario = HorarioDisponible.objects.create(
            fecha=fecha_futura,
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            disponible=True,
        )

    def test_agendar_concurrente_solo_crea_una_cita(self):
        resultados = []

        def intentar_agendar(documento, caso_id):
            try:
                cliente = Client(raise_request_exception=False)
                cliente.login(documento=documento, password='Password123')
                response = cliente.post('/agendar-cita/', {
                    'caso_id': caso_id,
                    'fecha': self.horario.fecha.strftime('%Y-%m-%d'),
                    'hora': '10:00',
                    'tipo_atencion': 'presencial',
                })
                resultados.append(response.status_code)
            except Exception:
                resultados.append('locked')
            finally:
                connection.close()

        original_excepthook = threading.excepthook
        threading.excepthook = lambda args: None

        try:
            thread_a = threading.Thread(
                target=intentar_agendar,
                args=('2222222222', self.caso_a.pk),
            )
            thread_b = threading.Thread(
                target=intentar_agendar,
                args=('3333333333', self.caso_b.pk),
            )

            thread_a.start()
            thread_b.start()
            thread_a.join()
            thread_b.join()
        finally:
            threading.excepthook = original_excepthook

        citas_horario = Cita.objects.filter(horario=self.horario)
        self.assertEqual(citas_horario.count(), 1)

        self.horario.refresh_from_db()
        self.assertFalse(self.horario.disponible)
