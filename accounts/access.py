STAFF_ROLES = frozenset({'admin', 'support_agent', 'support_manager', 'it_agent',
    'finance_agent', 'logistics_agent', 'moderator'})

def can_finance(identity):
    return identity.get('role') == 'admin' or (identity.get('role') == 'finance_agent'
        and identity.get('department') == 'payments')

def navigation(request):
    identity = request.session.get('node_user', {})
    return {'nexora_identity': identity, 'nexora_is_admin': identity.get('role') == 'admin',
            'nexora_can_finance': can_finance(identity),
            'support_filters': [('unassigned', 'Neatribuite'), ('my', 'Ticketele mele'),
                                ('all', 'Toate'), ('open', 'Deschise'), ('pending', 'În așteptare'),
                                ('closed', 'Rezolvate'), ('urgent', 'Urgente')],
            'support_priorities': ['low', 'normal', 'high', 'urgent'],
            'support_statuses': ['open', 'pending', 'closed']}

def admin_access(request):
    return request.session.get('node_user', {}).get('role') == 'admin'

def finance_access(request):
    return can_finance(request.session.get('node_user', {}))
