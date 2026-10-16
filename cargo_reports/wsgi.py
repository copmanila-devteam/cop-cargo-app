"""
WSGI config for cargo_reports project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

path = '/opt/bitnami/apache/htdocs/cargo_reports'

if path not in sys.path:
	sys.path.append(path)


from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'cargo_reports.settings'

application = get_wsgi_application()
