from django import setup
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultorio.settings')
setup()

from citas.models import Cita
from usuarios.models import Usuario
from notificaciones.models import Notificacion
from notificaciones.services import crear_notificaciones_reagendamiento

secretarias = list(Usuario.objects.filter(rol='secretaria'))
count = 0
for cita in Cita.objects.filter(fecha_reagendamiento__isnull=False):
    existing = Notificacion.objects.filter(
        usuario__in=secretarias,
        tipo='reagendamiento',
        mensaje__contains=f'cita del beneficiario {cita.beneficiario.nombre_completo}',
    )
    if not existing:
        crear_notificaciones_reagendamiento(cita, secretarias)
        count += 1
        print('creadas_notificaciones_para_cita', cita.id)

print('total_creadas', count)
