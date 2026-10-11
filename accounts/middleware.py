from django.utils.translation import gettext as _
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from .access import STAFF_ROLES, can_finance
from .node_api import NodeAPIError, node_request

class NexoraAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        path = request.path
        if not path.startswith('/admin/') or path in {'/admin/login/', '/admin/logout/'} or not request.user.is_authenticated:
            return self.get_response(request)
        try:
            identity = node_request(request, 'GET', '/auth/me')
        except NodeAPIError as error:
            if error.status_code in {401, 403}:
                logout(request)
                return redirect('admin:login')
            return render(request, 'admin/backend_unavailable.html', status=503)
        role = identity.get('role')
        if role not in STAFF_ROLES or identity.get('banned'):
            logout(request)
            return redirect('admin:login')
        request.session['node_user'] = {
            'id': str(identity.get('_id') or identity.get('id') or ''),
            'username': identity.get('username', ''), 'email': identity.get('email', ''),
            'role': role, 'department': identity.get('department', '')}
        if request.user.is_superuser != (role == 'admin'):
            request.user.is_superuser = role == 'admin'
            request.user.save(update_fields=['is_superuser'])
        common = path in {'/admin/', '/admin/dashboard/', '/admin/node-me/'} or path.startswith('/admin/support/')
        finance = path.startswith('/admin/withdrawals/') and can_finance(identity)
        if role != 'admin' and not (common or finance):
            return HttpResponseForbidden(_("Access is restricted for your role and department."))
        return self.get_response(request)
