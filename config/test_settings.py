from .settings import *  # noqa: F403

# Keep automated tests independent of credentials in .env and remote databases.
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
