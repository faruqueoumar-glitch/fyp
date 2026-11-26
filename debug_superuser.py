import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings.dev'

import django
django.setup()

from app.models import CustomUser

user = CustomUser._base_manager.get(email='faruqueoumar@gmail.com')
print('user.email:', user.email)
print('user.is_superuser:', user.is_superuser)
print('user.pharmacy_id:', user.pharmacy_id)
print('user.is_active:', user.is_active)