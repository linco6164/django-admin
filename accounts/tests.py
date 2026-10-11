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
