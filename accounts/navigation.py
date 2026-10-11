"""Request-time Unfold translations; importing settings must not load catalogs."""
from copy import deepcopy

from django.conf import settings
from django.utils.translation import gettext


def site_subheader(request):
    return gettext('Marketplace Administration')


def sidebar_navigation(request):
    groups = deepcopy(settings.NEXORA_NAVIGATION)

    def translate_items(items):
        for item in items:
            if 'title' in item:
                item['title'] = gettext(item['title'])
            translate_items(item.get('items', []))

    translate_items(groups)
    return groups
