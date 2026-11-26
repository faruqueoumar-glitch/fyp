import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings.dev'

import django
django.setup()

from app.models import CustomUser
from django.test import Client
import re

# Get the superuser
user = CustomUser._base_manager.get(email='faruqueoumar@gmail.com')
print('User is_superuser:', user.is_superuser)
print('User is_staff:', user.is_staff)
print('User pharmacy_id:', user.pharmacy_id)
print('User is_active:', user.is_active)

# Create test client and login
client = Client()

# First get the login page to get CSRF token
response = client.get('/login/')
print('GET /login/ status:', response.status_code)

# Get CSRF token from the form
csrf_token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode()).group(1)
print('CSRF token:', csrf_token)

# Try to login with the password we set
login_data = {
    'csrfmiddlewaretoken': csrf_token,
    'identifier': 'faruqueoumar@gmail.com',
    'password': 'admin123'
}
response = client.post('/login/', login_data, follow=True)
print('POST /login/ status:', response.status_code)
print('Redirect chain:', [(r.status_code, r.url) for r in response.redirect_chain])

# Check where we ended up
if hasattr(response, 'redirect_chain') and response.redirect_chain:
    for r in response.redirect_chain:
        print('  Redirect to:', r[0], r[1] if len(r) > 1 else '')

# Try to access /founder/ 
print()
print('--- Testing /founder/ access ---')
response = client.get('/founder/', follow=False)
print('GET /founder/ status (no follow):', response.status_code)
if hasattr(response, 'get'):
    print('GET /founder/ redirect location:', response.get('Location', 'N/A'))