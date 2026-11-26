import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings.dev')

import django
django.setup()

from app.models import CustomUser, Pharmacy

print("=== Superusers ===")
su = CustomUser._base_manager.filter(is_superuser=True)
print(f"Count: {su.count()}")
for u in su:
    print(f"  Email: {u.email}, pharmacy_id: {u.pharmacy_id}, is_staff: {u.is_staff}, is_superuser: {u.is_superuser}")

print("\n=== Pharmacies ===")
p = Pharmacy._base_manager.all()
print(f"Count: {p.count()}")
for ph in p:
    print(f"  ID: {ph.id}, Name: {ph.shop_name}, is_active: {ph.is_active}")

print("\n=== Current pharmacy context ===")
from app.tenancy import get_current_pharmacy_id
print(f"get_current_pharmacy_id(): {get_current_pharmacy_id()}")