from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home_view, name='home'),
    path('estudiante/home/', views.estudiante_home_view, name='estudiante_home'),
    path('profesor/home/', views.profesor_home_view, name='profesor_home'),
    path('citas/<int:pk>/cancelar/', views.cancelar_cita_view, name='cancelar_cita'),
    path('citas/<int:pk>/posponer/', views.posponer_cita_view, name='posponer_cita'),
    path('citas/<int:pk>/reagendar/', views.reagendar_cita_view, name='reagendar_cita'),
    path('citas/<int:pk>/confirmar/', views.confirmar_cita_view, name='confirmar_cita'),
    path('citas/<int:pk>/asistencia/', views.marcar_asistencia_view, name='marcar_asistencia'),
    path('gestionar-citas/', views.gestionar_citas_view, name='gestionar_citas'),
    path('gestionar-casos/', views.gestionar_casos_view, name='gestionar_casos'),
    path('agendar-cita/', views.agendar_cita_view, name='agendar_cita'),
    path('usuarios/<int:usuario_id>/historial/', views.historial_usuario_view, name='historial_usuario'),
]