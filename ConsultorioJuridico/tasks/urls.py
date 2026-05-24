from django.urls import path
from .views import (
    register_view,
    login_view,
    logout_view,
    dashboard_beneficiario,
    dashboard_estudiante,
    dashboard_profesor,
    dashboard_admin,
    dashboard_secretaria,
)

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    path("dashboard/beneficiario/", dashboard_beneficiario, name="dashboard_beneficiario"),
    path("dashboard/estudiante/", dashboard_estudiante, name="dashboard_estudiante"),
    path("dashboard/profesor/", dashboard_profesor, name="dashboard_profesor"),
    path("dashboard/admin/", dashboard_admin, name="dashboard_admin"),
    path("dashboard/secretaria/", dashboard_secretaria, name="dashboard_secretaria"),
]