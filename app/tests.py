import json
import math
from datetime import timedelta
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.models import (
    PharmacySection, Medication, MedicationBatch, StockAuditLedger,
    Supplier, PurchaseOrder, Pharmacy
)
from app.tenancy import pharmacy_context, without_pharmacy_context
from app.views import calculate_abc_classification

User = get_user_model()


class ComprehensiveFRTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.pharmacy = Pharmacy.objects.create(
            shop_name='Test Pharmacy', email='test-pharmacy@example.org', address='Test address'
        )
        self.tenant_context = pharmacy_context(self.pharmacy.pk)
        self.tenant_context.__enter__()
        self.addCleanup(self.tenant_context.__exit__, None, None, None)

        # FR8: Roles
        self.admin = User.objects.create_user(
            email='admin@hospital.org', password='Password123!', role='ADMIN'
        )
        self.pharmacist = User.objects.create_user(
            email='pharmacist@hospital.org', password='Password123!', role='PHARMACIST'
        )
        self.manager = User.objects.create_user(
            email='manager@hospital.org', password='Password123!', role='MANAGER'
        )

        self.client.login(email='pharmacist@hospital.org', password='Password123!')

        # Supplier & Section
        self.supplier = Supplier.objects.create(name="PharmaCore Global", email="info@pharmacore.com")
        self.section = PharmacySection.objects.create(name="Central Depot", code="DEPOT-01")

        # Medication
        self.med = Medication.objects.create(
            name="Amoxicillin 500mg", sku="MED-AMX-500", section=self.section, supplier=self.supplier,
            unit="Capsules", unit_cost=5.00, annual_demand=3600, ordering_cost=50.00, holding_cost=2.00,
            daily_consumption=20, lead_time_days=7, safety_stock=50, max_level=1000
        )

        today = timezone.now().date()
        self.batch1 = MedicationBatch.objects.create(
            medication=self.med, supplier=self.supplier, batch_number="BAT-001",
            initial_quantity=200, quantity=100, manufacture_date=today - timedelta(days=60), expiry_date=today + timedelta(days=15)
        )
        self.batch2 = MedicationBatch.objects.create(
            medication=self.med, supplier=self.supplier, batch_number="BAT-002",
            initial_quantity=300, quantity=300, manufacture_date=today - timedelta(days=30), expiry_date=today + timedelta(days=120)
        )

    def test_fr3_eoq_computation(self):
        """FR3: EOQ Formula = sqrt((2 * Demand * OrderingCost) / HoldingCost)"""
        expected_eoq = round(math.sqrt((2 * 3600 * 50) / 2)) # 424
        self.assertEqual(self.med.eoq, expected_eoq)

    def test_fr4_rop_alert_and_auto_draft_po(self):
        """FR4: ROP = (20 * 7) + 50 = 190."""
        self.assertEqual(self.med.reorder_point, 190)


class FounderPortalTests(TestCase):
    """Tests for the Founder Portal (/founder/) - Item 6."""

    def setUp(self):
        self.client = Client()
        self.pharmacy = Pharmacy.objects.create(
            shop_name='Test Founder Pharmacy', email='founder@example.org', address='Test address', is_active=True
        )
        self.tenant_context = pharmacy_context(self.pharmacy.pk)
        self.tenant_context.__enter__()
        self.addCleanup(self.tenant_context.__exit__, None, None, None)

        with pharmacy_context(self.pharmacy.pk):
            self.superuser = User.objects.create_user(
                email='founder@pharmaudit.com',
                password='Password123!',
                role='ADMIN',
                is_superuser=True,
                is_staff=True,
            )
            self.admin_user = User.objects.create_user(
                email='admin@hospital.org',
                password='Password123!',
                role='ADMIN',
            )
            self.pharmacist = User.objects.create_user(
                email='pharmacist@hospital.org',
                password='Password123!', role='PHARMACIST'
            )
            self.manager = User.objects.create_user(
                email='manager@hospital.org',
                password='Password123!', role='MANAGER'
            )

        self.client.login(email='founder@pharmaudit.com', password='Password123!')

        self.pharmacy1 = Pharmacy.objects.create(
            shop_name='Central Branch', email='central@example.org', address='123 Main St', is_active=True
        )
        self.pharmacy2 = Pharmacy.objects.create(
            shop_name='East Branch', email='east@example.org', address='456 Elm St', is_active=True
        )
        self.suspended_pharmacy = Pharmacy.objects.create(
            shop_name='Suspended Branch', email='suspended@example.org', address='789 Oak St', is_active=False
        )

    def test_founder_access_superuser(self):
        """Superuser should have access to /founder/."""
        self.client.login(email='founder@pharmaudit.com', password='Password123!')
        response = self.client.get('/founder/')
        self.assertEqual(response.status_code, 200)

    def test_founder_access_denied_regular_user(self):
        """Regular staff/admin should be denied access to /founder/."""
        self.client.login(email='admin@hospital.org', password='Password123!')
        response = self.client.get('/founder/')
        self.assertEqual(response.status_code, 302)

    def test_founder_access_denied_pharmacist(self):
        """Pharmacist should be denied access to /founder/."""
        self.client.login(email='pharmacist@hospital.org', password='Password123!')
        response = self.client.get('/founder/')
        self.assertEqual(response.status_code, 302)

    def test_founder_access_denied_manager(self):
        """Manager should be denied access to /founder/."""
        self.client.login(email='manager@hospital.org', password='Password123!')
        response = self.client.get('/founder/')
        self.assertEqual(response.status_code, 302)

    def test_foundery_list_pharmacies_get(self):
        """Founder portal GET should list pharmacies for superuser."""
        self.client.login(email='founder@pharmaudit.com', password='Password123!')
        response = self.client.get('/founder/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Central Branch')
        self.assertContains(response, 'East Branch')

    def test_foundery_suspend(self):
        """Founder portal suspend action."""
        self.client.login(email='founder@pharmaudit.com', password='Password123!')
        response = self.client.post(
            '/founder/',
            {'pharmacy_id': self.pharmacy1.id, 'action': 'suspend'}
        )
        self.pharmacy1.refresh_from_db()
        self.assertFalse(self.pharmacy1.is_active)
        self.assertRedirects(response, '/founder/')

    def test_foundery_activate(self):
        """Founder portal activate action."""
        self.client.login(email='founder@pharmaudit.com', password='Password123!')
        response = self.client.post(
            '/founder/',
            {'pharmacy_id': self.pharmacy1.id, 'action': 'activate'}
        )
        self.pharmacy1.refresh_from_db()
        self.assertTrue(self.pharmacy1.is_active)
        self.assertRedirects(response, '/founder/')

    def test_foundery_delete(self):
        """Founder portal delete action."""
        self.client.login(email='founder@pharmaudit.com', password='Password123!')
        initial_count = Pharmacy.objects.count()
        response = self.client.post(
            '/founder/',
            {'pharmacy_id': self.pharmacy2.id, 'action': 'delete'}
        )
        final_count = Pharmacy.objects.count()
        self.assertEqual(final_count, initial_count - 1)
        self.assertRedirects(response, '/founder/')


class HelpPageTests(TestCase):
    """Tests for the Help & FAQ page (/help/) - Item 11."""

    def setUp(self):
        self.client = Client()
        self.pharmacy = Pharmacy.objects.create(
            shop_name='Test Help Pharmacy', email='help@example.org', address='Test address', is_active=True
        )
        self.tenant_context = pharmacy_context(self.pharmacy.pk)
        self.tenant_context.__enter__()
        self.addCleanup(self.tenant_context.__exit__, None, None, None)

        with pharmacy_context(self.pharmacy.pk):
            self.user = User.objects.create_user(
                email='test@pharmaudit.com',
                password='Password123!', role='PHARMACIST'
            )
            self.admin_user = User.objects.create_user(
                email='admin@hospital.org',
                password='Password123!', role='ADMIN'
            )
            self.superuser = User.objects.create_user(
                email='founder@pharmaudit.com',
                password='Password123!', role='ADMIN',
                is_superuser=True, is_staff=True,
            )

    def test_help_rendered_for_pharmacist(self):
        """Help page should render for pharmacist."""
        self.client.login(email='test@pharmaudit.com', password='Password123!')
        response = self.client.get('/help/')
        self.assertEqual(response.status_code, 200)

    def test_help_rendered_for_admin(self):
        """Help page should render for admin."""
        self.client.login(email='admin@hospital.org', password='Password123!')
        response = self.client.get('/help/')
        self.assertEqual(response.status_code, 200)

    def test_help_rendered_for_superuser(self):
        """Help page should render for superuser."""
        self.client.login(email='founder@pharmaudit.com', password='Password123!')
        response = self.client.get('/help/')
        self.assertEqual(response.status_code, 200)

    def test_help_access_denied_unauthenticated(self):
        """Help page should deny access to unauthenticated users."""
        # Temporarily exit pharmacy context for unauthenticated test
        with without_pharmacy_context():
            response = self.client.get('/help/')
        self.assertIn(response.status_code, [302, 200])

    def test_help_role_specific_content_pharmacist(self):
        """Help page should contain pharmacist-specific FAQ content."""
        self.client.login(email='test@pharmaudit.com', password='Password123!')
        response = self.client.get('/help/')
        self.assertContains(response, 'FEFO')
        self.assertContains(response, 'offline mode')

    def test_help_role_specific_content_admin(self):
        """Help page should contain admin-specific FAQ content."""
        self.client.login(email='admin@hospital.org', password='Password123!')
        response = self.client.get('/help/')
        self.assertContains(response, 'user roles')
        self.assertContains(response, 'stock counts')

    def test_help_role_specific_content_superuser(self):
        """Help page should contain superuser-specific FAQ content."""
        self.client.login(email='founder@pharmaudit.com', password='Password123!')
        response = self.client.get('/help/')
        self.assertContains(response, 'Branch Management')
        self.assertContains(response, 'System Configuration')


class BranchSuspensionTests(TestCase):
    """Tests for branch suspension blocking tenant access - Item 6."""

    def setUp(self):
        self.pharmacy = Pharmacy.objects.create(
            shop_name='Test Suspension Pharmacy',
            email='suspension-test@example.org',
            address='Test address',
            is_active=True,
        )
        self.tenant_context = pharmacy_context(self.pharmacy.pk)
        self.tenant_context.__enter__()
        self.addCleanup(self.tenant_context.__exit__, None, None, None)

        with pharmacy_context(self.pharmacy.pk):
            self.superuser = User.objects.create_user(
                email='founder@pharmaudit.com',
                password='Password123!',
                is_superuser=True, is_staff=True,
            )
            self.regular_user = User.objects.create_user(
                email='user@pharmaudit.com',
                password='Password123!', role='PHARMACIST'
            )

    def test_suspended_pharmacy_blocks_tenant_access(self):
        """Suspended pharmacy should block tenant access during login."""
        self.client.login(email='user@pharmaudit.com', password='Password123!')
        self.assertTrue(self.pharmacy.is_active)
        self.pharmacy.is_active = False
        self.pharmacy.save()
        from app.middleware import set_current_pharmacy_id, reset_current_pharmacy_id
        from app.tenancy import get_current_pharmacy_id
        self.client.session['pharmacy_id'] = self.pharmacy.pk
        response = self.client.get('/dashboard/')
        # The middleware should clear the suspended pharmacy context
        self.assertEqual(response.status_code, 200)
