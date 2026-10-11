from django.utils.translation import gettext as _
from urllib.parse import urlsplit
import requests
from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
import logging

class NodeAPIError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code

def api_request(method, endpoint, token=None, **kwargs):
    if not endpoint.startswith('/') or endpoint.startswith('//') or urlsplit(endpoint).scheme:
        raise NodeAPIError(_("The API route is invalid."))
    headers = dict(kwargs.pop('headers', {}))
    headers['Accept'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        response = requests.request(method, settings.NODE_API_URL.rstrip('/') + endpoint,
            headers=headers, timeout=settings.NODE_API_TIMEOUT, allow_redirects=False, **kwargs)
    except requests.RequestException as error:
        raise NodeAPIError(_("The Nexora backend cannot be reached. Try again later.")) from error
    if response.status_code == 401:
        raise NodeAPIError(_("Your Nexora session has expired. Sign in again."), 401)
    if response.status_code == 403:
        raise NodeAPIError(_("You do not have the required permission."), 403)
    if not 200 <= response.status_code < 300:
        raise NodeAPIError(_('The backend rejected the request (HTTP %(status)s).') % {'status': response.status_code}, response.status_code)
    if response.status_code == 204:
        return {}
    try:
        data = response.json()
    except ValueError as error:
        raise NodeAPIError(_("The backend did not return valid JSON.")) from error
    if not isinstance(data, dict) or data.get('success') is False:
        raise NodeAPIError(_("The backend returned an invalid response or rejected the operation."))
    return data

def node_request(request, method, endpoint, **kwargs):
    token = request.session.get('node_token')
    if not token:
        raise NodeAPIError(_("Nexora authentication is required."), 401)
    try:
        result = api_request(method, endpoint, token=token, **kwargs)
        if method.upper() in {'POST', 'PATCH', 'PUT', 'DELETE'} and request.user.is_authenticated:
            try:
                LogEntry.objects.create(
                    user_id=request.user.pk, object_repr=endpoint[:200],
                    action_flag=CHANGE, change_message=f'Nexora API: {method.upper()} {endpoint}',
                )
            except Exception:
                # A completed backend operation must not be presented as failed.
                logging.getLogger(__name__).exception('Cannot record Nexora operation audit')
        return result
    except NodeAPIError as error:
        if error.status_code == 401:
            request.session.pop('node_token', None)
            request.session.pop('node_user', None)
        raise
