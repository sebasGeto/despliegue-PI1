from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import LoginForm, RegistroPaso1Form, RegistroPaso2Form
from .models import Usuario
from .emails import enviar_correo_bienvenida


def login_view(request):
    """Vista de inicio de sesión."""
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        documento = form.cleaned_data["documento"]
        password = form.cleaned_data["password"]
        user = authenticate(request, documento=documento, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")

        return render(request, "usuarios/login.html", {
            "form": form,
            "error": "Documento o contraseña inválidos.",
        })

    return render(request, "usuarios/login.html", {"form": form})


def registro_paso1_view(request):
    """Vista del paso 1 del registro: datos personales."""
    if request.method == "POST":
        form = RegistroPaso1Form(request.POST)
        if form.is_valid():
            request.session["registro_datos"] = form.cleaned_data
            return redirect("registro_paso2")
    else:
        datos_guardados = request.session.get("registro_datos", {})
        form = RegistroPaso1Form(initial=datos_guardados)

    return render(request, "usuarios/registro_paso1.html", {"form": form})


def registro_paso2_view(request):
    """Vista del paso 2 del registro: contraseña y consentimiento."""
    if "registro_datos" not in request.session:
        return redirect("registro_paso1")

    if request.method == "POST":
        form = RegistroPaso2Form(request.POST)
        if form.is_valid():
            datos = request.session["registro_datos"]
            user = Usuario.objects.create_user(
                documento=datos["documento"],
                correo=datos["correo"],
                nombre_completo=datos["nombre_completo"],
                telefono=datos.get("telefono", ""),
                direccion=datos.get("direccion", ""),
                acepta_tratamiento_datos=form.cleaned_data["acepta_tratamiento_datos"],
                password=form.cleaned_data["password1"],
            )

            try:
                enviar_correo_bienvenida(user)
                mensaje_registro = (
                    "Registro exitoso. Revise su correo e inicie sesión con sus credenciales."
                )
            except Exception:
                mensaje_registro = (
                    "Registro exitoso. No se pudo enviar el correo de bienvenida, "
                    "pero ya puede iniciar sesión con sus credenciales."
                )

            del request.session["registro_datos"]
            messages.success(request, mensaje_registro)
            return redirect("login")
    else:
        form = RegistroPaso2Form()

    return render(request, "usuarios/registro_paso2.html", {"form": form})


def logout_view(request):
    """Vista de cierre de sesión."""
    logout(request)
    return redirect("login")