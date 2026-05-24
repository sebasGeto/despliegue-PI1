from django.urls import path
from . import views

urlpatterns = [
    path('recordatorios/bitacora/', views.bitacora_recordatorios_view, name='bitacora_recordatorios'),
]