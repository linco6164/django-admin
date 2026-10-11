from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .access import STAFF_ROLES
from .node_api import NodeAPIError, api_request

class NodeAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, otp=None, **kwargs):
        if request is None or not username or not password:
            return None
        try:
            data = api_request('POST', '/auth/login', json={'email': username, 'password': password})
            if data.get('requiresTwoFactor'):
                if not otp:
                    return None
                data = api_request('POST', '/auth/2fa/login', json={'userId': data.get('userId'), 'token': otp})
            token = data.get('token')
            if not token:
                return None
            identity = api_request('GET', '/auth/me', token=token)
        except NodeAPIError:
            return None
        if identity.get('role') not in STAFF_ROLES or identity.get('banned') or not identity.get('email'):
            return None
        user, _ = User.objects.get_or_create(username=identity['email'])
        user.email = identity['email']
        user.is_active = user.is_staff = True
        user.is_superuser = identity['role'] == 'admin'
        user.set_unusable_password()
        user.save()
        request.session['node_token'] = token
        request.session['node_user'] = {
            'id': str(identity.get('_id') or identity.get('id') or ''),
            'username': identity.get('username', ''), 'email': identity['email'],
            'role': identity['role'], 'department': identity.get('department', '')}
        return user

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id, is_active=True).first()
