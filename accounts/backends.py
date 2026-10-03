import requests

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User


class NodeAuthBackend(BaseBackend):

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs
    ):
        if not username or not password:
            return None

        try:
            response = requests.post(
                "https://api.nx-store.com/auth/login",
                json={
                    "email": username,
                    "password": password,
                },
                timeout=15,
            )

        except requests.RequestException as error:
            print("Node API error:", error)
            return None

        if response.status_code != 200:
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        if not data.get("success"):
            return None

        if data.get("requiresTwoFactor"):
            return None

        user_data = data.get("user")

        if not user_data:
            return None

        if user_data.get("role") != "admin":
            return None

        token = data.get("token")

        if not token:
            return None

        email = user_data.get("email")

        if not email:
            return None

        django_user, _ = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
            },
        )

        django_user.email = email
        django_user.is_active = True
        django_user.is_staff = True
        django_user.is_superuser = True

        django_user.set_unusable_password()
        django_user.save()

        if request is not None:
            request.session["node_token"] = token

            request.session["node_user"] = {
                "id": user_data.get("id"),
                "username": user_data.get("username"),
                "email": user_data.get("email"),
                "role": user_data.get("role"),
            }

        return django_user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None