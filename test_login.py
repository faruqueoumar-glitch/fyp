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
print('User pharmacy_id:', user.pharmacy_id)
print('User is_active:', user.is_active)

# Create test client
client = Client(csrf=False)

# First get the login page to get CSRF token
response = client.get('/login/')
print('GET /login/ status:', response.status_code)

# Get CSRF token from the form
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())
if csrf_match:
    csrf_token = csrf_match.group(1)
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
    print('Final response URL:', response.url if hasattr(response, 'url') else 'N/A')
    print('Final response status:', response.status_code if hasattr(response, 'status_code') else 'N/A')
    
    # Try to access /founder/ 
    print()
    print('--- Testing /founder/ access ---')
    response = client.get('/founder/', follow=False)
    print('GET /founder/ status (no follow):', response.status_code)
    if hasattr(response, 'get'):
        print('GET /founder/ redirect location:', response.get('Location', 'N/A'))
else:
    print('No CSRF token found on login page')