from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import RegistroBeneficiarioForm, LoginForm
from .models import Rol


def register_view(request):
    if request.method == "POST":
        form = RegistroBeneficiarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard_beneficiario")
    else:
        form = RegistroBeneficiarioForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        documento = form.cleaned_data["documento"]
        password = form.cleaned_data["password"]

        user = authenticate(request, documento=documento, password=password)

        if user is not None:
            login(request, user)

            if user.rol == Rol.BENEFICIARIO:
                return redirect("dashboard_beneficiario")
            elif user.rol == Rol.ESTUDIANTE:
                return redirect("dashboard_estudiante")
            elif user.rol == Rol.PROFESOR:
                return redirect("dashboard_profesor")
            elif user.rol == Rol.ADMINISTRADOR:
                return redirect("dashboard_admin")
            elif user.rol == Rol.SECRETARIA:
                return redirect("dashboard_secretaria")

        return render(request, "login.html", {
            "form": form,
            "error": "Documento o contraseña inválidos."
        })

    return render(request, "login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_beneficiario(request):
    return render(request, "dashboard_beneficiario.html")


@login_required
def dashboard_estudiante(request):
    return render(request, "dashboard_estudiante.html")


@login_required
def dashboard_profesor(request):
    return render(request, "dashboard_profesor.html")


@login_required
def dashboard_admin(request):
    return render(request, "dashboard_admin.html")


@login_required
def dashboard_secretaria(request):
    return render(request, "dashboard_secretaria.html")