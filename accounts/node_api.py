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
        raise NodeAPIError('Ruta API este invalidă.')
    headers = dict(kwargs.pop('headers', {}))
    headers['Accept'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        response = requests.request(method, settings.NODE_API_URL.rstrip('/') + endpoint,
            headers=headers, timeout=settings.NODE_API_TIMEOUT, allow_redirects=False, **kwargs)
    except requests.RequestException as error:
        raise NodeAPIError('Backendul Nexora nu poate fi accesat. Reîncearcă mai târziu.') from error
    if response.status_code == 401:
        raise NodeAPIError('Sesiunea Nexora a expirat. Autentifică-te din nou.', 401)
    if response.status_code == 403:
        raise NodeAPIError('Nu ai permisiunea necesară.', 403)
    if not 200 <= response.status_code < 300:
        raise NodeAPIError(f'Backendul a refuzat cererea (HTTP {response.status_code}).', response.status_code)
    if response.status_code == 204:
        return {}
    try:
        data = response.json()
    except ValueError as error:
        raise NodeAPIError('Backendul nu a returnat JSON valid.') from error
    if not isinstance(data, dict) or data.get('success') is False:
        raise NodeAPIError('Backendul a returnat un răspuns invalid sau a refuzat operațiunea.')
    return data

def node_request(request, method, endpoint, **kwargs):
    token = request.session.get('node_token')
    if not token:
        raise NodeAPIError('Autentificarea Nexora este necesară.', 401)
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
