from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

class NexoraAuthenticationForm(AdminAuthenticationForm):
    otp = forms.CharField(label='Cod 2FA (dacă este activat)', required=False, max_length=6,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'inputmode': 'numeric'}))
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password,
                otp=self.cleaned_data.get('otp'))
            if self.user_cache is None:
                raise ValidationError('Date sau cod 2FA invalide, acces refuzat ori backend indisponibil.')
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class StaffCreationForm(forms.Form):
    username = forms.CharField(label='Username', min_length=3, max_length=150)
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Parolă inițială', min_length=12, widget=forms.PasswordInput)
    fullName = forms.CharField(label='Nume complet', required=False, max_length=200)
    phone = forms.CharField(label='Telefon', required=False, max_length=40)
    role = forms.ChoiceField(label='Rol', choices=[(role, role) for role in (
        'support_agent', 'support_manager', 'it_agent', 'finance_agent', 'logistics_agent', 'moderator')])
    department = forms.ChoiceField(label='Departament', choices=[(value, value) for value in (
        'general', 'call_center', 'it', 'payments', 'orders', 'logistics', 'moderation', 'account_security')])

    def clean(self):
        data = super().clean()
        if data.get('role') == 'finance_agent' and data.get('department') != 'payments':
            self.add_error('department', 'Agenții financiari trebuie atribuiți departamentului payments.')
        return data
