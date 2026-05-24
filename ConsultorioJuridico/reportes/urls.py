from django.urls import path

from reportes.views import exportar_reporte_pdf, exportar_reporte_excel, dashboard_metricas_view

app_name = 'reportes'

urlpatterns = [
    path('reportes/exportar/pdf/',   exportar_reporte_pdf,   name='exportar_pdf'),
    path('reportes/exportar/excel/', exportar_reporte_excel, name='exportar_excel'),
    path('reportes/dashboard/', dashboard_metricas_view, name='dashboard_metricas'),
]