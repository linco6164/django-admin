from django.contrib import admin
from django.contrib.auth.models import User, Group

admin.site.site_url = 'https://nx-store.com'


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass