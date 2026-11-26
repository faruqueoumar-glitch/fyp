import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings.dev'

import django
django.setup()

from django.test import RequestFactory
from app.middleware import PharmacyContextMiddleware
from app.models import CustomUser

# Create a mock request (POST to login)
factory = RequestFactory()
request = factory.post('/login/', {'identifier': 'faruqueoumar@gmail.com', 'password': 'test123'})

# Set up the user as the superuser first
user = CustomUser._base_manager.get(email='faruqueoumar@gmail.com')
print("User:", user.email)
print("User is_superuser:", user.is_superuser)
print("User pharmacy_id:", user.pharmacy_id)
print("User is_active:", user.is_active)

# Now process through middleware
middleware = PharmacyContextMiddleware(lambda r: None)
try:
    middleware.__call__(request)
    print("\nAfter middleware:")
    print("Request pharmacy_id:", request.pharmacy_id)
    print("Request pharmacy:", request.pharmacy)
except Exception as e:
    print("Error during middleware:", e)