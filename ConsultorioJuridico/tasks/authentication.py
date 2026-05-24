from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class DocumentoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        documento = kwargs.get("documento") or username

        if documento is None or password is None:
            return None

        try:
            user = UserModel.objects.get(documento=documento)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None