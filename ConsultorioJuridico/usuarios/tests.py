from django.test import TestCase
from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario, Rol
from usuarios.forms import LoginForm, RegistroPaso1Form, RegistroPaso2Form
from django.core import mail
from django.test import override_settings

# Modelo Usuario

#Clase que hereda los TestCase
class UsuarioModelTest(TestCase):  
    
    #Datos que se usaran para realizar las pruebas
    def setUp(self): 
        self.usuario = Usuario.objects.create_user(
            documento="123456",
            correo="test@correo.com",
            nombre_completo="Ana García",
            password="clave1234",
        )

    #Test: un usuario es creado correctamente mediante su documento y su nombre
    def test_usuario_creado_correctamente(self):
        """El usuario se crea con los campos esperados."""
        self.assertEqual(self.usuario.documento, "123456")
        self.assertEqual(self.usuario.correo, "test@correo.com")
        self.assertEqual(self.usuario.nombre_completo, "Ana García")
    
    def test_rol_por_defecto_es_beneficiario(self):
        """Un usuario nuevo debe tener rol 'beneficiario' por defecto."""
        self.assertEqual(self.usuario.rol, Rol.BENEFICIARIO)

    def test_username_field_es_documento(self):
        """El campo de autenticación principal debe ser 'documento'."""
        self.assertEqual(Usuario.USERNAME_FIELD, "documento")

    def test_campo_username_no_existe(self):
        """El campo 'username' heredado de AbstractUser debe estar eliminado."""
        self.assertIsNone(Usuario.username)

    def test_str_incluye_nombre_y_documento(self):
        """El __str__ del usuario debe incluir nombre y documento."""
        self.assertIn("Ana García", str(self.usuario))
        self.assertIn("123456", str(self.usuario))

    def test_crear_usuario_con_rol_estudiante(self):
        """Se puede crear un usuario con un rol diferente al por defecto."""
        estudiante = Usuario.objects.create_user(
            documento="999",
            correo="est@correo.com",
            nombre_completo="Luis Pérez",
            password="clave1234",
            rol=Rol.ESTUDIANTE,
        )
        self.assertEqual(estudiante.rol, Rol.ESTUDIANTE)

    def test_acepta_tratamiento_datos_false_por_defecto(self):
        """El campo acepta_tratamiento_datos debe ser False por defecto."""
        self.assertFalse(self.usuario.acepta_tratamiento_datos)

    def test_documento_es_unico(self):
        """No se puede crear un segundo usuario con el mismo documento."""
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                documento="123456",  # ya existe
                correo="otro@correo.com",
                nombre_completo="Otro Usuario",
                password="clave1234",
            )

    def test_correo_es_unico(self):
        """No se puede crear un segundo usuario con el mismo correo."""
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                documento="999888",
                correo="test@correo.com",  # ya existe
                nombre_completo="Otro Usuario",
                password="clave1234",
            )

# Autentificacion por documento

class AutenticacionPorDocumentoTest(TestCase):
    """Pruebas del backend de autenticación DocumentoBackend."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            documento="DOC001",
            correo="doc@correo.com",
            nombre_completo="Usuario Prueba",
            password="segura123",
        )
        self.client = Client()

    def test_login_con_documento_correcto(self):
        """El usuario puede autenticarse con documento y contraseña válidos."""
        response = self.client.post(reverse("login"), {
            "documento": "DOC001",
            "password": "segura123",
        })
        # Tras login exitoso redirige al home
        self.assertRedirects(response, reverse("home"))

    def test_login_con_contrasena_incorrecta(self):
        """Login con contraseña incorrecta no autentica al usuario."""
        response = self.client.post(reverse("login"), {
            "documento": "DOC001",
            "password": "incorrecta",
        })
        # Debe permanecer en la página de login con mensaje de error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "inválidos")

    def test_login_con_documento_inexistente(self):
        """Login con documento que no existe no autentica."""
        response = self.client.post(reverse("login"), {
            "documento": "NOEXISTE",
            "password": "cualquiera",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "inválidos")

    def test_usuario_no_autenticado_redirige_al_login(self):
        """Una vista protegida redirige al login si el usuario no está autenticado."""
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_logout_cierra_sesion(self):
        """Después de logout, el usuario ya no está autenticado."""
        self.client.login(documento="DOC001", password="segura123")
        self.client.get(reverse("logout"))
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")


#Formularios de autentificacion

class LoginFormTest(TestCase):
    """Pruebas del formulario de login."""

    def test_formulario_valido_con_datos_correctos(self):
        form = LoginForm(data={"documento": "123", "password": "abc"})
        self.assertTrue(form.is_valid())

    def test_formulario_invalido_sin_documento(self):
        form = LoginForm(data={"password": "abc"})
        self.assertFalse(form.is_valid())
        self.assertIn("documento", form.errors)

    def test_formulario_invalido_sin_password(self):
        form = LoginForm(data={"documento": "123"})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

#Registro 

class RegistroPaso1FormTest(TestCase):
    """Pruebas del formulario del paso 1 de registro."""

    def _datos_validos(self):
        return {
            "documento": "555",
            "nombre_completo": "Carlos López",
            "correo": "carlos@correo.com",
            "telefono": "3001234567",
            "direccion": "Calle 10 # 5-20",
        }

    def test_formulario_paso1_valido(self):
        form = RegistroPaso1Form(data=self._datos_validos())
        self.assertTrue(form.is_valid())

    def test_formulario_paso1_sin_correo(self):
        datos = self._datos_validos()
        del datos["correo"]
        form = RegistroPaso1Form(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

    def test_formulario_paso1_sin_documento(self):
        datos = self._datos_validos()
        del datos["documento"]
        form = RegistroPaso1Form(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("documento", form.errors)


class RegistroPaso2FormTest(TestCase):
    """Pruebas del formulario del paso 2 de registro."""

    def test_formulario_paso2_valido(self):
        form = RegistroPaso2Form(data={
            "password1": "clave1234",
            "password2": "clave1234",
            "acepta_tratamiento_datos": True,
        })
        self.assertTrue(form.is_valid())

    def test_contrasenas_no_coinciden(self):
        form = RegistroPaso2Form(data={
            "password1": "clave1234",
            "password2": "diferente",
            "acepta_tratamiento_datos": True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Las contraseñas no coinciden", str(form.errors))

    def test_sin_aceptar_tratamiento_datos(self):
        form = RegistroPaso2Form(data={
            "password1": "clave1234",
            "password2": "clave1234",
            "acepta_tratamiento_datos": False,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("acepta_tratamiento_datos", form.errors)


class RegistroVistaTest(TestCase):
    """Pruebas del flujo de registro en 2 pasos vía vistas."""

    def setUp(self):
        self.client = Client()

    def test_paso1_get_renderiza_formulario(self):
        response = self.client.get(reverse("registro_paso1"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/registro_paso1.html")

    def test_paso1_post_valido_redirige_a_paso2(self):
        response = self.client.post(reverse("registro_paso1"), {
            "documento": "777",
            "nombre_completo": "María Suárez",
            "correo": "maria@correo.com",
            "telefono": "3009876543",
            "direccion": "Av. 3 # 1-10",
        })
        self.assertRedirects(response, reverse("registro_paso2"))

    def test_paso2_sin_sesion_previa_redirige_a_paso1(self):
        """Si se accede a paso 2 sin haber completado paso 1, redirige."""
        response = self.client.get(reverse("registro_paso2"))
        self.assertRedirects(response, reverse("registro_paso1"))

    def test_registro_completo_crea_usuario(self):
        """El flujo completo de 2 pasos crea un usuario en la base de datos."""
        # Paso 1
        self.client.post(reverse("registro_paso1"), {
            "documento": "888",
            "nombre_completo": "Pedro Rivas",
            "correo": "pedro@correo.com",
            "telefono": "3001111111",
            "direccion": "Cra 5",
        })
        # Paso 2
        self.client.post(reverse("registro_paso2"), {
            "password1": "clave1234",
            "password2": "clave1234",
            "acepta_tratamiento_datos": True,
        })
        self.assertTrue(Usuario.objects.filter(documento="888").exists())

    def test_registro_completo_acepta_tratamiento_datos(self):
        """El usuario creado debe tener acepta_tratamiento_datos = True."""
        self.client.post(reverse("registro_paso1"), {
            "documento": "889",
            "nombre_completo": "Sara Gómez",
            "correo": "sara@correo.com",
            "telefono": "3002222222",
            "direccion": "Cll 8",
        })
        self.client.post(reverse("registro_paso2"), {
            "password1": "clave1234",
            "password2": "clave1234",
            "acepta_tratamiento_datos": True,
        })
        usuario = Usuario.objects.get(documento="889")
        self.assertTrue(usuario.acepta_tratamiento_datos)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_registro_completo_envia_correo_bienvenida(self):
        """Al registrarse, el usuario debe recibir un correo de bienvenida."""
        self.client.post(reverse("registro_paso1"), {
            "documento": "890",
            "nombre_completo": "Laura Torres",
            "correo": "laura@correo.com",
            "telefono": "3003333333",
            "direccion": "Cll 9",
        })
        response = self.client.post(reverse("registro_paso2"), {
            "password1": "clave1234",
            "password2": "clave1234",
            "acepta_tratamiento_datos": True,
        })

        self.assertRedirects(response, reverse("login"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["laura@correo.com"])
        self.assertIn("Bienvenido", mail.outbox[0].subject)
        self.assertIn("Laura Torres", mail.outbox[0].body)


    class SendEmailViewTest(TestCase):
        def setUp(self):
            self.usuario