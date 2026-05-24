from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
from citas.models import Caso, HorarioDisponible, Cita
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Populate database with test data'

    def handle(self, *args, **options):
        # Crear usuarios
        beneficiario = Usuario.objects.create_user(
            documento='12345678',
            correo='beneficiario@example.com',
            nombre_completo='Juan Pérez',
            password='password123',
            rol='beneficiario',
            telefono='123456789',
            direccion='Calle Falsa 123',
            acepta_tratamiento_datos=True
        )

        secretaria = Usuario.objects.create_user(
            documento='87654321',
            correo='secretaria@example.com',
            nombre_completo='María García',
            password='password123',
            rol='secretaria',
            telefono='987654321',
            direccion='Avenida Siempre Viva 456',
            acepta_tratamiento_datos=True
        )

        estudiante = Usuario.objects.create_user(
            documento='11223344',
            correo='estudiante@example.com',
            nombre_completo='Pedro López',
            password='password123',
            rol='estudiante',
            telefono='555666777',
            direccion='Plaza Mayor 789',
            acepta_tratamiento_datos=True
        )

        self.stdout.write(self.style.SUCCESS('Usuarios creados'))

        # Crear casos
        caso1 = Caso.objects.create(
            codigo='CASO001',
            beneficiario=beneficiario,
            sala_juridica='civil',
            descripcion='Caso de divorcio',
            estado='asignado',
            estudiante_asignado=estudiante
        )

        caso2 = Caso.objects.create(
            codigo='CASO002',
            beneficiario=beneficiario,
            sala_juridica='laboral',
            descripcion='Demanda laboral',
            estado='en_estudio'
        )

        caso3 = Caso.objects.create(
            codigo='CASO003',
            beneficiario=beneficiario,
            sala_juridica='penal',
            descripcion='Caso penal',
            estado='cerrado'
        )

        self.stdout.write(self.style.SUCCESS('Casos creados'))

        # Crear horarios disponibles
        today = date.today()
        horario1 = HorarioDisponible.objects.create(
            fecha=today + timedelta(days=1),
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            disponible=True
        )

        horario2 = HorarioDisponible.objects.create(
            fecha=today + timedelta(days=2),
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0),
            disponible=True
        )

        horario3 = HorarioDisponible.objects.create(
            fecha=today + timedelta(days=3),
            hora_inicio=time(11, 0),
            hora_fin=time(12, 0),
            disponible=True
        )

        horario4 = HorarioDisponible.objects.create(
            fecha=today + timedelta(days=4),
            hora_inicio=time(14, 0),
            hora_fin=time(15, 0),
            disponible=True
        )

        horario5 = HorarioDisponible.objects.create(
            fecha=today + timedelta(days=5),
            hora_inicio=time(15, 0),
            hora_fin=time(16, 0),
            disponible=True
        )

        self.stdout.write(self.style.SUCCESS('Horarios creados'))

        # Crear citas
        cita1 = Cita.objects.create(
            beneficiario=beneficiario,
            caso=caso1,
            horario=horario1,
            tipo_atencion='presencial',
            estado='confirmada',
            motivo='Consulta inicial',
            fecha_confirmacion=timezone.now()
        )

        cita2 = Cita.objects.create(
            beneficiario=beneficiario,
            caso=caso2,
            horario=horario2,
            tipo_atencion='telefonica',
            estado='pendiente',
            motivo='Seguimiento'
        )

        cita3 = Cita.objects.create(
            beneficiario=beneficiario,
            caso=caso3,
            horario=horario3,
            tipo_atencion='virtual',
            estado='cumplida',
            motivo='Cierre de caso',
            fecha_confirmacion=timezone.now() - timedelta(days=1)
        )

        cita4 = Cita.objects.create(
            beneficiario=beneficiario,
            caso=caso1,
            horario=horario4,
            tipo_atencion='presencial',
            estado='cancelada',
            motivo='Cancelación por enfermedad',
            fecha_cancelacion=timezone.now(),
            motivo_cancelacion='El beneficiario está enfermo',
            cancelada_por=secretaria
        )

        # Para reagendamiento, crear una cita reagendada
        cita5 = Cita.objects.create(
            beneficiario=beneficiario,
            caso=caso2,
            horario=horario5,
            tipo_atencion='virtual',
            estado='confirmada',
            motivo='Reagendamiento de consulta',
            fecha_confirmacion=timezone.now(),
            horario_anterior=horario2,
            fecha_reagendamiento=timezone.now(),
            reagendada_por=secretaria
        )

        cita6 = Cita.objects.create(
            beneficiario=beneficiario,
            caso=caso1,
            horario=HorarioDisponible.objects.create(
                fecha=today + timedelta(days=6),
                hora_inicio=time(16, 0),
                hora_fin=time(17, 0),
                disponible=False  # Ocupado
            ),
            tipo_atencion='telefonica',
            estado='no_asistio',
            motivo='Consulta no asistida',
            fecha_confirmacion=timezone.now() - timedelta(days=2)
        )

        self.stdout.write(self.style.SUCCESS('Citas creadas'))