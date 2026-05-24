from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, PerfilBeneficiario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = (
        "id",
        "documento",
        "nombre_completo",
        "correo",
        "rol",
        "is_active",
        "is_staff",
    )
    list_filter = ("rol", "is_active", "is_staff", "is_superuser")
    search_fields = ("documento", "nombre_completo", "correo")
    ordering = ("documento",)

    fieldsets = (
        ("Credenciales", {"fields": ("documento", "password")}),
        ("Información personal", {
            "fields": (
                "nombre_completo",
                "correo",
                "telefono",
                "direccion",
            )
        }),
        ("Rol y consentimiento", {
            "fields": (
                "rol",
                "acepta_tratamiento_datos",
            )
        }),
        ("Permisos", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Fechas importantes", {
            "fields": (
                "last_login",
                "date_joined",
            )
        }),
    )

    add_fieldsets = (
        ("Crear usuario", {
            "classes": ("wide",),
            "fields": (
                "documento",
                "nombre_completo",
                "correo",
                "telefono",
                "direccion",
                "rol",
                "acepta_tratamiento_datos",
                "password1",
                "password2",
                "is_active",
                "is_staff",
            ),
        }),
    )


@admin.register(PerfilBeneficiario)
class PerfilBeneficiarioAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "ciudad", "barrio", "estrato")
    search_fields = (
        "usuario__nombre_completo",
        "usuario__documento",
        "ciudad",
    )