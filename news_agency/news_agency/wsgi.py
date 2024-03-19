"""
WSGI config for news_agency project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys

path = '/home/sc21hta/Web_Services_-_Web_Data/news_agency'
if path not in sys.path:
    sys.path.insert(0, path)

# Ensure the 'DJANGO_SETTINGS_MODULE' is set to your project's settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'news_agency.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
