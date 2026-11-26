import django
os.environ["DJANGO_SETTINGS_MODULE"] = "src.settings.dev"
import os
django.setup()
print('is_superuser:', u.is_superuser, 'is_staff:', u.is_staff)
u = CustomUser._base_manager.get(email="faruqueoumar@gmail.com")
from app.models import CustomUser
