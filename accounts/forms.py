from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .labels import DEPARTMENT_LABELS, ROLE_LABELS

class NexoraAuthenticationForm(AdminAuthenticationForm):
    otp = forms.CharField(label=_('2FA code (if enabled)'), required=False, max_length=6,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'inputmode': 'numeric'}))
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password,
                otp=self.cleaned_data.get('otp'))
            if self.user_cache is None:
                raise ValidationError(_('Invalid credentials or 2FA code, access denied, or backend unavailable.'))
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class StaffCreationForm(forms.Form):
    username = forms.CharField(label=_('Username'), min_length=3, max_length=150)
    email = forms.EmailField(label=_('Email'))
    password = forms.CharField(label=_('Initial password'), min_length=12, widget=forms.PasswordInput)
    fullName = forms.CharField(label=_('Full name'), required=False, max_length=200)
    phone = forms.CharField(label=_('Phone'), required=False, max_length=40)
    role = forms.ChoiceField(label=_('Role'), choices=[(role, ROLE_LABELS[role]) for role in (
        'support_agent', 'support_manager', 'it_agent', 'finance_agent', 'logistics_agent', 'moderator')])
    department = forms.ChoiceField(label=_('Department'), choices=[(value, DEPARTMENT_LABELS[value]) for value in (
        'general', 'call_center', 'it', 'payments', 'orders', 'logistics', 'moderation', 'account_security')])

    def clean(self):
        data = super().clean()
        if data.get('role') == 'finance_agent' and data.get('department') != 'payments':
            self.add_error('department', _('Finance agents must belong to the Payments department.'))
        return data
