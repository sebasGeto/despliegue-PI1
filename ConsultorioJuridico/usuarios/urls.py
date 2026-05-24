from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("registro/", views.registro_paso1_view, name="registro_paso1"),
    path("registro/paso2/", views.registro_paso2_view, name="registro_paso2"),
    path("logout/", views.logout_view, name="logout"),
]
