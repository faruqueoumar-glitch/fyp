import getpass
import os
import secrets
import sys
from django.core.management.base import BaseCommand
from app.models import CustomUser, Pharmacy, pharmacy_context


def generate_founder_id():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    existing = set(CustomUser._base_manager.values_list('pha_user_id', flat=True))
    while True:
        candidate = 'PHA.OS/FND-' + ''.join(secrets.choice(alphabet) for _ in range(6))
        if candidate not in existing:
            return candidate


class Command(BaseCommand):
    help = 'Create or promote a Founder (superuser) account with proper tenant context.'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Founder email address')
        parser.add_argument('--password', type=str, help='Founder password')
        parser.add_argument('--first-name', type=str, default='Platform', help='First name')
        parser.add_argument('--last-name', type=str, default='Founder', help='Last name')

    def handle(self, *args, **options):
        email = (options.get('email') or os.environ.get('FOUNDER_EMAIL') or '').strip().lower()
        password = options.get('password') or os.environ.get('FOUNDER_PASSWORD') or ''
        first_name = options.get('first_name') or os.environ.get('FOUNDER_FIRST_NAME') or 'Platform'
        last_name = options.get('last_name') or os.environ.get('FOUNDER_LAST_NAME') or 'Founder'

        if not email:
            if sys.stdin.isatty():
                email = input('Founder Email: ').strip().lower()
            else:
                self.stdout.write('Skipping create_founder (FOUNDER_EMAIL not set).')
                return

        if not email:
            self.stderr.write(self.style.ERROR('Email is required.'))
            return

        if not password and sys.stdin.isatty():
            password = getpass.getpass('Founder Password (leave blank to keep existing if user exists): ').strip()

        # Ensure at least one Pharmacy record exists for PharmacyOwnedModel scoping
        pharmacy = Pharmacy._base_manager.order_by('id').first()
        if not pharmacy:
            pharmacy = Pharmacy._base_manager.create(
                shop_name='PharmaAudit HQ',
                email=email,
                is_active=True,
            )

        existing_user = CustomUser._base_manager.filter(email__iexact=email).first()
        if existing_user:
            existing_user.is_superuser = True
            existing_user.is_staff = True
            existing_user.is_active = True
            existing_user.role = 'ADMIN'
            if not existing_user.pha_user_id or not existing_user.pha_user_id.startswith('PHA.OS/FND-'):
                existing_user.pha_user_id = generate_founder_id()
            if password:
                existing_user.set_password(password)
            existing_user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Promoted existing user {existing_user.email} to Founder Superuser ({existing_user.pha_user_id}).'
            ))
            return

        if not password:
            self.stderr.write(self.style.ERROR('Password is required when creating a new Founder user.'))
            return

        with pharmacy_context(pharmacy.pk):
            user = CustomUser.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                pharmacy_id=None,
                pha_user_id=generate_founder_id(),
            )

        self.stdout.write(self.style.SUCCESS(
            f'Created Founder Superuser {user.email} ({user.pha_user_id}) scoped to {pharmacy.shop_name}.'
        ))
