from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator

from .models import LogRecordatorio


@login_required
def bitacora_recordatorios_view(request):
    if request.user.rol not in ['administrador', 'secretaria']:
        messages.error(request, 'No tiene permisos para acceder a la bitácora de recordatorios.')
        return redirect('home')

    logs = LogRecordatorio.objects.select_related(
        'cita',
        'cita__beneficiario',
        'cita__horario',
    ).all()

    canal_filtro = request.GET.get('canal', '')
    estado_filtro = request.GET.get('estado', '')

    if canal_filtro in ['email', 'sms']:
        logs = logs.filter(canal=canal_filtro)

    if estado_filtro in ['pendiente', 'enviado', 'fallido']:
        logs = logs.filter(estado=estado_filtro)

    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recordatorios/bitacora_recordatorios.html', {
        'page_obj': page_obj,
        'canal_filtro': canal_filtro,
        'estado_filtro': estado_filtro,
        'canal_choices': LogRecordatorio.CANAL_CHOICES,
        'estado_choices': LogRecordatorio.ESTADO_CHOICES,
    })