from unittest.mock import Mock, patch
import requests
from django.contrib.auth.models import User
from django.template.loader import get_template
from django.test import TestCase, RequestFactory
from pathlib import Path
from django.conf import settings
from .backends import NodeAuthBackend
from .node_api import NodeAPIError, api_request, node_request

class IntegrationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.identity = {'_id': 'abc', 'email': 'agent@nexora.test', 'role': 'finance_agent', 'department': 'payments'}
    def request(self):
        request = self.factory.get('/admin/dashboard/')
        request.session = {}
        return request
    @patch('accounts.backends.api_request')
    def test_finance_login_does_not_grant_superuser(self, api):
        api.side_effect = [{'token': 'secret'}, self.identity]
        request = self.request()
        user = NodeAuthBackend().authenticate(request, username='agent@nexora.test', password='test')
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(request.session['node_user']['department'], 'payments')
    @patch('accounts.backends.api_request')
    def test_two_factor_uses_verified_identity(self, api):
        api.side_effect = [{'requiresTwoFactor': True, 'userId': 'abc'}, {'token': 'secret'}, self.identity]
        user = NodeAuthBackend().authenticate(self.request(), username='agent@nexora.test', password='test', otp='123456')
        self.assertIsNotNone(user)
        self.assertEqual(api.call_args_list[1].kwargs['json']['token'], '123456')
    @patch('accounts.backends.api_request')
    def test_regular_or_banned_users_cannot_login(self, api):
        for identity in [dict(self.identity, role='user'), dict(self.identity, banned=True)]:
            api.side_effect = [{'token': 'secret'}, identity]
            self.assertIsNone(NodeAuthBackend().authenticate(self.request(), username='x', password='y'))
    @patch('accounts.node_api.requests.request')
    def test_no_content_is_success(self, call):
        call.return_value = Mock(status_code=204)
        self.assertEqual(api_request('DELETE', '/admin/listings/abc', token='secret'), {})
        self.assertFalse(call.call_args.kwargs['allow_redirects'])
    @patch('accounts.node_api.requests.request')
    def test_expired_session_clears_token(self, call):
        call.return_value = Mock(status_code=401)
        request = self.request()
        request.session.update(node_token='secret', node_user=self.identity)
        with self.assertRaises(NodeAPIError):
            node_request(request, 'GET', '/auth/me')
        self.assertNotIn('node_token', request.session)
    @patch('accounts.node_api.requests.request')
    def test_errors_do_not_expose_backend_body(self, call):
        call.return_value = Mock(status_code=500, text='private database secret')
        with self.assertRaises(NodeAPIError) as error:
            api_request('GET', '/admin/stats')
        self.assertNotIn('private', str(error.exception))
    @patch('accounts.node_api.requests.request')
    def test_timeout_returns_safe_error(self, call):
        call.side_effect = requests.Timeout('secret')
        with self.assertRaises(NodeAPIError) as error:
            api_request('GET', '/admin/stats')
        self.assertNotIn('secret', str(error.exception))
    @patch('accounts.node_api.requests.request')
    def test_application_failure_is_not_success(self, call):
        call.return_value = Mock(status_code=200)
        call.return_value.json.return_value = {'success': False}
        with self.assertRaises(NodeAPIError):
            api_request('POST', '/support/staff/tickets/abc/assign')
    def test_all_templates_compile(self):
        for path in (settings.BASE_DIR / 'accounts/templates/admin').glob('*.html'):
            with self.subTest(template=path.name):
                get_template('admin/' + path.name)

class AccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='agent', is_staff=True)
        self.client.force_login(self.user, backend='accounts.backends.NodeAuthBackend')
        session = self.client.session
        session['node_token'] = 'secret'
        session.save()
    @patch('accounts.middleware.node_request')
    def test_support_agent_cannot_access_finance_or_users(self, api):
        api.return_value = {'role': 'support_agent', 'department': 'general'}
        for path in ['/admin/withdrawals/', '/admin/marketplace-users/', '/admin/notifications/']:
            self.assertEqual(self.client.get(path).status_code, 403)
    @patch('accounts.middleware.node_request')
    def test_finance_wrong_department_is_denied(self, api):
        api.return_value = {'role': 'finance_agent', 'department': 'general'}
        self.assertEqual(self.client.get('/admin/withdrawals/').status_code, 403)
    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_finance_payments_access(self, identity, api):
        identity.return_value = {'role': 'finance_agent', 'department': 'payments'}
        api.return_value = {'data': [], 'total': 0, 'pages': 1}
        self.assertEqual(self.client.get('/admin/withdrawals/').status_code, 200)
    @patch('accounts.middleware.node_request')
    def test_revoked_access_logs_out(self, api):
        api.return_value = {'role': 'user'}
        self.assertEqual(self.client.get('/admin/dashboard/').status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)
    @patch('accounts.middleware.node_request')
    def test_unavailable_backend_fails_closed(self, api):
        api.side_effect = NodeAPIError('unavailable')
        self.assertEqual(self.client.get('/admin/dashboard/').status_code, 503)
    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_support_queue_renders_and_escapes_messages(self, identity, api):
        identity.return_value = {'role': 'support_agent', 'department': 'general'}
        api.side_effect = [{'departments': ['general']}, {'stats': {'open': 1}},
            {'tickets': {'tickets': [{'_id': 'abc', 'subject': '<script>alert(1)</script>', 'user': {}, 'messages': []}], 'total': 1}}]
        response = self.client.get('/admin/support/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '&lt;script&gt;')
    @patch('accounts.middleware.node_request')
    def test_mutation_requires_post(self, api):
        api.return_value = {'role': 'support_agent', 'department': 'general'}
        self.assertEqual(self.client.get('/admin/support/abc/action/').status_code, 405)

class OperationalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.user, backend='accounts.backends.NodeAuthBackend')
        session = self.client.session
        session['node_token'] = 'secret'
        session.save()
    @patch('accounts.operations.node_request')
    @patch('accounts.middleware.node_request')
    def test_staff_creation_sends_backend_role_and_department(self, identity, api):
        identity.return_value = {'role': 'admin'}
        api.return_value = {'success': True}
        response = self.client.post('/admin/team/create/', {'username': 'finance', 'email': 'finance@nexora.test',
            'password': 'temporary-password-42', 'role': 'finance_agent', 'department': 'payments'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(api.call_args.kwargs['json']['department'], 'payments')
    @patch('accounts.operations.node_request')
    @patch('accounts.middleware.node_request')
    def test_finance_creation_rejects_wrong_department(self, identity, api):
        identity.return_value = {'role': 'admin'}
        response = self.client.post('/admin/team/create/', {'username': 'finance', 'email': 'finance@nexora.test',
            'password': 'temporary-password-42', 'role': 'finance_agent', 'department': 'general'})
        self.assertEqual(response.status_code, 200)
        api.assert_not_called()
    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_withdrawal_cannot_complete_without_transfer_confirmation(self, identity, api):
        identity.return_value = {'role': 'admin'}
        response = self.client.post('/admin/withdrawals/abc/action/', {'action': 'approve'})
        self.assertEqual(response.status_code, 302)
        api.assert_not_called()
    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_confirmed_withdrawal_uses_real_endpoint(self, identity, api):
        identity.return_value = {'role': 'admin'}
        api.return_value = {'success': True}
        response = self.client.post('/admin/withdrawals/abc/action/', {'action': 'approve', 'transfer_confirmed': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(api.call_args.args[2], '/admin/withdrawals/abc/approve')
    def test_login_displays_two_factor_input(self):
        self.client.logout()
        self.assertContains(self.client.get('/admin/login/'), 'name="otp"')

class AuditTests(TestCase):
    @patch('accounts.node_api.requests.request')
    def test_successful_mutation_records_operator_without_payload(self, call):
        from django.contrib.admin.models import LogEntry
        user = User.objects.create_user(username='operator', is_staff=True)
        request = RequestFactory().post('/admin/support/abc/action/')
        request.user = user
        request.session = {'node_token': 'secret-token'}
        call.return_value = Mock(status_code=200)
        call.return_value.json.return_value = {'success': True}
        node_request(request, 'POST', '/support/staff/tickets/abc/messages', json={'message': 'private text'})
        entry = LogEntry.objects.get(user=user)
        self.assertIn('/support/staff/tickets/abc/messages', entry.change_message)
        self.assertNotIn('private text', entry.change_message)
        self.assertNotIn('secret-token', entry.change_message)


class SupportDisplayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='display-admin', is_staff=True, is_superuser=True)
        self.client.force_login(self.user, backend='accounts.backends.NodeAuthBackend')
        session = self.client.session
        session['node_token'] = 'test-token'
        session.save()
        # Same state as the existing ticket verified in the backend: closed and assigned.
        self.ticket = {'_id': 'existing-ticket', 'subject': 'Existing closed request',
                       'department': 'call_center', 'status': 'closed', 'priority': 'normal',
                       'assignedTo': {'_id': 'agent', 'username': 'Assigned agent'},
                       'user': {'username': 'Customer'}, 'messages': []}

    def api_response(self, request, method, endpoint, **kwargs):
        if endpoint.endswith('/info'):
            return {'role': 'admin', 'department': 'general', 'departments': ['general', 'call_center', 'payments']}
        if endpoint.endswith('/stats'):
            return {'stats': {'open': 0, 'closed': 1, 'total': 1, 'unassigned': 0, 'urgent': 0, 'myTickets': 0}}
        return {'tickets': {'tickets': [dict(self.ticket)], 'total': 1}}

    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_default_filter_includes_closed_assigned_ticket(self, identity, api):
        identity.return_value = {'role': 'admin'}
        api.side_effect = self.api_response
        response = self.client.get('/admin/support/')
        self.assertContains(response, 'Existing closed request')
        self.assertEqual(response.context['active_filter'], 'all')
        self.assertEqual(api.call_args.kwargs['params'], {})
        self.assertEqual(response.context['total'], 1)

    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_assignment_filter_is_only_sent_when_requested(self, identity, api):
        identity.return_value = {'role': 'admin'}
        api.side_effect = self.api_response
        self.client.get('/admin/support/?filter=unassigned')
        self.assertEqual(api.call_args.kwargs['params'], {'assignedTo': 'unassigned'})

    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_statistics_failure_does_not_hide_tickets(self, identity, api):
        identity.return_value = {'role': 'admin'}
        def response(request, method, endpoint, **kwargs):
            if endpoint.endswith('/stats'):
                raise NodeAPIError('Statistics unavailable')
            return self.api_response(request, method, endpoint, **kwargs)
        api.side_effect = response
        self.assertContains(self.client.get('/admin/support/'), 'Existing closed request')

    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_supported_ticket_response_shapes(self, identity, api):
        identity.return_value = {'role': 'admin'}
        payloads = [{'tickets': [self.ticket], 'total': 1}, {'data': [self.ticket], 'total': 1},
                    {'data': {'tickets': [self.ticket], 'total': 1}}]
        for payload in payloads:
            with self.subTest(payload=payload.keys()):
                api.side_effect = [self.api_response(None, None, '/info'), {}, payload]
                self.assertContains(self.client.get('/admin/support/'), 'Existing closed request')

    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_invalid_response_shows_error_instead_of_empty_queue(self, identity, api):
        identity.return_value = {'role': 'admin'}
        api.side_effect = [{}, {}, {'unexpected': []}]
        response = self.client.get('/admin/support/', headers={'Accept-Language': 'en'})
        self.assertContains(response, 'The backend returned an invalid ticket list.')

    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_romanian_and_english_support_options(self, identity, api):
        identity.return_value = {'role': 'admin'}
        api.side_effect = self.api_response
        romanian = self.client.get('/admin/support/', headers={'Accept-Language': 'ro'})
        for text in ['Actualizează', 'Aplică filtrele', 'Toate ticketele', 'Plăți', 'General']:
            self.assertContains(romanian, text)
        self.assertNotContains(romanian, 'Ă‚')
        english = self.client.get('/admin/support/', headers={'Accept-Language': 'en'})
        for text in ['Refresh', 'Apply filters', 'All tickets', 'Payments']:
            self.assertContains(english, text)
        self.assertNotContains(english, 'Actualizează')

    @patch('accounts.views.node_request')
    @patch('accounts.middleware.node_request')
    def test_withdrawals_translate_without_changing_status_values(self, identity, api):
        identity.return_value = {'role': 'admin'}
        api.return_value = {'data': [], 'total': 0, 'pages': 0}
        romanian = self.client.get('/admin/withdrawals/', headers={'Accept-Language': 'ro'})
        for text in ['Retrageri', 'În așteptare', 'Aplică', 'Pagina 1 din 1']:
            self.assertContains(romanian, text)
        self.assertContains(romanian, 'value="pending"')
        english = self.client.get('/admin/withdrawals/', headers={'Accept-Language': 'en'})
        self.assertContains(english, 'Withdrawals')
        self.assertContains(english, 'Pending')

    def test_compiled_catalog_contains_new_translations(self):
        import gettext
        with open(settings.BASE_DIR / 'locale/ro/LC_MESSAGES/django.mo', 'rb') as handle:
            catalog = gettext.GNUTranslations(handle)
        self.assertEqual(catalog.gettext('Apply filters'), 'Aplică filtrele')
        self.assertEqual(catalog.gettext('Payments'), 'Plăți')
        self.assertEqual(catalog.gettext('All tickets'), 'Toate ticketele')


class StartupTranslationTests(TestCase):
    def test_settings_serialization_and_wsgi_start_before_registry_ready(self):
        import os
        import subprocess
        import sys

        environment = dict(os.environ, DJANGO_SETTINGS_MODULE='config.test_settings')
        script = '''
import json
from django.apps import apps
from django.conf import settings
assert not apps.apps_ready
json.dumps(settings.UNFOLD, default=str)
json.dumps(settings.NEXORA_NAVIGATION, default=str)
assert not apps.apps_ready
import config.wsgi
assert apps.ready
assert callable(config.wsgi.application)
print('startup OK')
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=settings.BASE_DIR,
                                env=environment, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('startup OK', result.stdout)

    def test_navigation_translates_per_request_without_mutating_settings(self):
        from django.utils.translation import override
        from .navigation import sidebar_navigation, site_subheader

        request = RequestFactory().get('/admin/')
        with override('ro'):
            romanian = sidebar_navigation(request)
            self.assertEqual(romanian[0]['items'][0]['title'], 'Panou de control')
            self.assertEqual(site_subheader(request), 'Administrare marketplace')
        with override('en'):
            english = sidebar_navigation(request)
            self.assertEqual(english[0]['items'][0]['title'], 'Dashboard')
            self.assertEqual(site_subheader(request), 'Marketplace Administration')
        self.assertEqual(settings.NEXORA_NAVIGATION[0]['items'][0]['title'], 'Dashboard')
