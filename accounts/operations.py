from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .forms import StaffCreationForm
from .node_api import NodeAPIError, node_request
from django.contrib.admin.models import LogEntry


@require_http_methods(['GET', 'POST'])
def staff_create(request):
    form = StaffCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            node_request(request, 'POST', '/admin/users', json=form.cleaned_data)
        except NodeAPIError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, 'Contul de agent a fost creat în backendul Nexora.')
            return redirect('marketplace_users')
    context = admin.site.each_context(request)
    context.update(title='Adaugă agent', form=form)
    return render(request, 'admin/staff_create.html', context)


def audit_log(request):
    context = admin.site.each_context(request)
    context.update(title='Istoric operațiuni', entries=LogEntry.objects.filter(
        change_message__startswith='Nexora API:'
    ).select_related('user').order_by('-action_time')[:100])
    return render(request, 'admin/operations_audit.html', context)
