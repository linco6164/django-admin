STAFF_ROLES = frozenset({'admin', 'support_agent', 'support_manager', 'it_agent',
    'finance_agent', 'logistics_agent', 'moderator'})

from django.utils.translation import gettext_lazy as _
from .labels import DEPARTMENT_LABELS, PRIORITY_LABELS, STATUS_LABELS, ROLE_LABELS, WITHDRAWAL_LABELS


def can_finance(identity):
    return identity.get('role') == 'admin' or (identity.get('role') == 'finance_agent'
        and identity.get('department') == 'payments')

def navigation(request):
    identity = request.session.get('node_user', {})
    return {'nexora_identity': identity, 'nexora_is_admin': identity.get('role') == 'admin',
            'nexora_can_finance': can_finance(identity),
            'nexora_role_label': ROLE_LABELS.get(identity.get('role'), identity.get('role', '')),
            'nexora_department_label': DEPARTMENT_LABELS.get(identity.get('department'), _('General')),
            'support_filters': [('all', _('All tickets')), ('unassigned', _('Unassigned')),
                                ('my', _('My tickets')), ('open', _('Open')),
                                ('pending', _('On hold')), ('closed', _('Resolved')), ('urgent', _('Urgent'))],
            'support_priorities': list(PRIORITY_LABELS.items()),
            'support_statuses': list(STATUS_LABELS.items()),
            'withdrawal_statuses': list(WITHDRAWAL_LABELS.items())}

def admin_access(request):
    return request.session.get('node_user', {}).get('role') == 'admin'

def finance_access(request):
    return can_finance(request.session.get('node_user', {}))
