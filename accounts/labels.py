from django.utils.translation import gettext_lazy as _

DEPARTMENT_LABELS = {
    'general': _('General'), 'call_center': _('Call center'),
    'it': _('IT'), 'payments': _('Payments'), 'orders': _('Orders'),
    'logistics': _('Logistics'), 'moderation': _('Moderation'),
    'account_security': _('Account security'), 'admin': _('Administration'),
}
PRIORITY_LABELS = {'low': _('Low'), 'normal': _('Normal'), 'high': _('High'), 'urgent': _('Urgent')}
STATUS_LABELS = {'open': _('Open'), 'pending': _('On hold'), 'closed': _('Resolved')}
WITHDRAWAL_LABELS = {
    'pending': _('Pending'), 'completed': _('Completed'),
    'rejected': _('Rejected'), 'failed': _('Failed'),
}
ROLE_LABELS = {
    'admin': _('Administrator'), 'support_agent': _('Support agent'),
    'support_manager': _('Support manager'), 'it_agent': _('IT agent'),
    'finance_agent': _('Finance agent'), 'logistics_agent': _('Logistics agent'),
    'moderator': _('Moderator'), 'user': _('User'),
}
