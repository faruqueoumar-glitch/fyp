#!/usr/bin/env python3
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings.dev'

import django
django.setup()

from app.models import CustomUser, Pharmacy
from django.test import RequestFactory
from app.middleware import PharmacyContextMiddleware
from django.contrib.auth import login as auth_login

print("=" * 60)
print("TEST 1: Check superuser state")
print("=" * 60)

user = CustomUser._base_manager.get(email='faruqueoumar@gmail.com')
print(f"User: {user.email}")
print(f"  is_superuser: {user.is_superuser}")
print(f"  is_staff: {user.is_staff}")
print(f"  pharmacy_id: {user.pharmacy_id}")
print(f"  is_active: {user.is_active}")

print("\n" + "=" * 60)
print("TEST 2: Check login view logic for superuser with pharmacy=None")
print("=" * 60)

# Simulate the login flow
# After successful authentication of superuser with pharmacy=None:

# Step 1: login() is called
# Step 2: Check user.pharmacy_id
if user.pharmacy_id:
    print("  user.pharmacy_id is set (unexpected for this test)")
else:
    print("  user.pharmacy_id is None (expected)")

# Step 3: Post-login redirect logic
# From lines 486-497 of views.py
next_url = None  # No 'next' parameter in our test
print(f"\n  next_url from request: {next_url}")

# The critical part - what happens after next_url check?
if next_url and False:  # next_url is None, so this block is skipped
    print("  next_url block entered (not our case)")
else:
    # Fall through to line 495-496
    if user.is_superuser:
        print("  REDIRECT to 'founder_dashboard' (this is the expected behavior)")
    else:
        print("  REDIRECT to 'dashboard'")

print("\n" + "=" * 60)
print("TEST 3: Check home_view logic")
print("=" * 60)

# home_view at lines 839-844
if user.is_superuser and not getattr(user, 'pharmacy_id', None):
    print("  home_view would redirect to 'founder_dashboard'")
else:
    print("  home_view would redirect to 'dashboard'")

print("\n" + "=" * 60)
print("TEST 4: Check founder_dashboard_view access")
print("=" * 60)

# founder_dashboard_view at lines 2151-2275
# Line 2153: if not request.user.is_superuser: return redirect('dashboard')
# A superuser with pharmacy=None should pass this check
print("  founder_dashboard_view check: request.user.is_superuser = True")
print("  → Would NOT redirect to dashboard, would proceed to render")

print("\n" + "=" * 60)
print("TEST 5: Middleware behavior with superuser pharmacy=None")
print("=" * 60)

factory = RequestFactory()
request = factory.get('/founder/')

# Simulate middleware processing
middleware = PharmacyContextMiddleware(lambda r: None)

# Set up the user on the request
from django.contrib.auth.models import AnonymousUser
request.user = user  # Set the superuser

try:
    middleware.__call__(request)
    print(f"  After middleware:")
    print(f"    request.pharmacy_id: {getattr(request, 'pharmacy_id', 'NOT SET')}")
    print(f"    request.pharmacy: {getattr(request, 'pharmacy', 'NOT SET')}")
    print(f"    user.pharmacy_id: {user.pharmacy_id}")
except Exception as e:
    print(f"  Error during middleware: {e}")

print("\n" + "=" * 60)
print("CONCLUSION")
print("=" * 60)
print("""
The code logic should work correctly for a superuser with pharmacy=None:
1. login_view redirects to founder_dashboard after login (line 495-496)
2. home_view redirects to founder_dashboard for superuser with no pharmacy (line 841-842)
3. founder_dashboard_view allows superusers through (line 2153)
4. Middleware sets request.pharmacy_id and request.pharmacy appropriately

If the superuser "cannot log in" or "cannot reach /founder/", the issue might be:
- Login form validation failure (wrong password, etc.)
- Session not being persisted properly
- Some other middleware or configuration issue

Let me run the actual Django server to test this empirically.
""")