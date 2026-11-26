#!/usr/bin/env python3
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings.dev'

import django
django.setup()

from app.models import CustomUser

print("Fixing superuser flag for faruqueoumar@gmail.com...")

user = CustomUser._base_manager.get(email='faruqueoumar@gmail.com')
print(f"Before - is_superuser: {user.is_superuser}, is_staff: {user.is_staff}")

# Fix the is_superuser flag
user.is_superuser = True
user.save()

# Verify
user.refresh_from_db()
print(f"After - is_superuser: {user.is_superuser}, is_staff: {user.is_staff}")

print("\nNow testing the login view logic...")
from django.test import RequestFactory
from app.middleware import PharmacyContextMiddleware

factory = RequestFactory()
request = factory.get('/login/')
request.user = user

# Check the already-authenticated path (lines 411-414)
if request.user.is_authenticated:
    if request.user.is_superuser:
        print("  ✓ login_view: Would redirect to 'founder_dashboard' (line 413)")
    else:
        print("  ✗ login_view: Would redirect to 'dashboard' (line 414) - BUG!")
else:
    print("  User not authenticated")