from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Rol, Permiso, UsuarioRol, RolPermiso


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ("documento", "nombre_completo", "correo", "rol", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = ("documento", "nombre_completo", "correo")
    ordering = ("documento",)

    fieldsets = (
        ("Credenciales", {"fields": ("documento", "password")}),
        ("Información personal", {
            "fields": ("nombre_completo", "correo", "telefono", "direccion")
        }),
        ("Rol y consentimiento", {
            "fields": ("rol", "acepta_tratamiento_datos")
        }),
        ("Permisos", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
    )

    add_fieldsets = (
        ("Crear usuario", {
            "classes": ("wide",),
            "fields": (
                "documento", "nombre_completo", "correo",
                "rol", "password1", "password2",
            ),
        }),
    )


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'descripcion')
    search_fields = ('nombre', 'codigo')


@admin.register(UsuarioRol)
class UsuarioRolAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol')
    list_filter = ('rol',)


@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ('rol', 'permiso')
    list_filter = ('rol',)
