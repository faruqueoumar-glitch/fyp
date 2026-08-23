import json
import math
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from app.models import (
    PharmacySection, Medication, MedicationBatch, StockAuditLedger,
    Supplier, PurchaseOrder
)
from app.views import calculate_abc_classification

User = get_user_model()


class ComprehensiveFRTests(TestCase):

    def setUp(self):
        self.client = Client()

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

        # Medication (Demand=3600, OrderCost=50, HoldingCost=2 -> EOQ = sqrt(2*3600*50/2) = sqrt(180000) = 424)
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
        """FR4: ROP = (20 * 7) + 50 = 190. Current stock = 400 > ROP -> Not triggered yet."""
        self.assertEqual(self.med.reorder_point, 190)

        # Reduce stock to below ROP (150 <= 190)
        self.batch1.quantity = 50
        self.batch1.save()
        self.batch2.quantity = 100
        self.batch2.save()

        self.assertLessEqual(self.med.current_stock, self.med.reorder_point)

        # Trigger auto draft PO as Pharmacist (who has acknowledge_rop)
        response = self.client.get(reverse('auto_generate_draft_po', args=[self.med.id]))
        # Pharmacist redirected to medications_list because they cannot approve POs
        self.assertRedirects(response, reverse('medications_list'))

        po = PurchaseOrder.objects.filter(supplier=self.supplier, status='DRAFT').first()
        self.assertIsNotNone(po)
        self.assertEqual(po.items.first().eoq_recommended_qty, self.med.eoq)

        # Trigger auto draft PO as Manager (who has acknowledge_rop AND can_approve_purchase_orders)
        self.client.login(email='manager@hospital.org', password='Password123!')
        response_mgr = self.client.get(reverse('auto_generate_draft_po', args=[self.med.id]))
        self.assertRedirects(response_mgr, reverse('purchase_orders'))
        self.client.login(email='pharmacist@hospital.org', password='Password123!')

    def test_physical_stock_adjustment(self):
        """Reconciles system inventory with physical count audit."""
        response = self.client.post(reverse('stock_adjustment'), {
            'medication': self.med.id,
            'actual_physical_count': 350,
            'reason': 'Routine Physical Stock Count Audit'
        })
        self.assertRedirects(response, reverse('medications_list'))
        self.med.refresh_from_db()
        self.assertEqual(self.med.current_stock, 350)

    def test_fr2_immutable_audit_trail_delete_prevention(self):
        """FR2: Delete must raise PermissionDenied"""
        log = StockAuditLedger.objects.create(
            user_identity='pharmacist@hospital.org',
            action_type='STOCK_RECEIPT',
            affected_entity='Medication',
            entity_pk=str(self.med.id)
        )
        with self.assertRaises(PermissionDenied):
            log.delete()

    def test_fr6_abc_classification(self):
        """FR6: Ranks drugs by annual consumption value"""
        med2 = Medication.objects.create(
            name="Cheap Drug", sku="MED-CHP-1", section=self.section, unit_cost=0.10, annual_demand=100
        )
        abc_data = calculate_abc_classification()
        self.assertEqual(len(abc_data), 2)
        # Higher consumption value drug is ranked #1 (Category A)
        self.assertEqual(abc_data[0]['medication'], self.med)
        self.assertEqual(abc_data[0]['category'], 'A')

    def test_fr9_csv_export(self):
        """FR9: Exports CSV report (Authorized for Manager with generate_reports)"""
        # Pharmacist should be denied
        res_pharma = self.client.get(reverse('export_report_csv') + '?type=stock_status')
        self.assertNotEqual(res_pharma.status_code, 200)

        # Manager is authorized
        self.client.login(email='manager@hospital.org', password='Password123!')
        response = self.client.get(reverse('export_report_csv') + '?type=stock_status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, 'Amoxicillin 500mg')
        self.client.login(email='pharmacist@hospital.org', password='Password123!')

    def test_explicit_role_permissions_matrix(self):
        """Explicitly test the granular RBAC permissions matrix for Admin, Pharmacist, and Manager."""
        # Admin Group (Identical capabilities to Superuser)
        admin_perms = {
            'manage_users': True,
            'configure_system': True,
            'manage_suppliers': True,
            'view_stock_dashboard': True,
            'search_drug_records': True,
            'view_audit_trail': True,
            'dispense_stock': True,
            'record_stock_receipt': True,
            'record_stock_adjustment': True,
            'approve_purchase_orders': True,
            'generate_reports': True,
            'review_abc_classification': True,
        }
        for perm, expected in admin_perms.items():
            self.assertEqual(
                self.admin.has_permission(perm),
                expected,
                f"Admin permission mismatch for {perm}: expected {expected}"
            )

        # Pharmacist Group
        pharmacist_perms = {
            'view_stock_dashboard': True,
            'record_stock_receipt': True,
            'dispense_stock': True,
            'acknowledge_rop': True,
            'record_stock_adjustment': True,
            'search_drug_records': True,
            'manage_users': False,
            'configure_system': False,
            'manage_suppliers': False,
            'approve_purchase_orders': False,
            'generate_reports': False,
            'review_abc_classification': False,
            'view_audit_trail': False,
        }
        for perm, expected in pharmacist_perms.items():
            self.assertEqual(
                self.pharmacist.has_permission(perm),
                expected,
                f"Pharmacist permission mismatch for {perm}: expected {expected}"
            )

        # Manager Group
        manager_perms = {
            'view_stock_dashboard': True,
            'acknowledge_rop': True,
            'search_drug_records': True,
            'generate_reports': True,
            'approve_purchase_orders': True,
            'review_abc_classification': True,
            'view_audit_trail': True,
            'manage_users': False,
            'configure_system': False,
            'manage_suppliers': False,
            'dispense_stock': False,
            'record_stock_receipt': False,
            'record_stock_adjustment': False,
        }
        for perm, expected in manager_perms.items():
            self.assertEqual(
                self.manager.has_permission(perm),
                expected,
                f"Manager permission mismatch for {perm}: expected {expected}"
            )

    def test_user_registration_flow(self):
        """Test public registration is disabled and admin staff provisioning creates new accounts with assigned roles."""
        # 1. Unauthenticated registration attempt must redirect to login
        self.client.logout()
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('login'))

        # 2. Admin provisions staff account with role
        self.client.login(email='admin@hospital.org', password='Password123!')
        res_create = self.client.post(reverse('manage_users'), {
            'action': 'create_user',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'email': 'jane.doe@hospital.org',
            'role': 'PHARMACIST',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertRedirects(res_create, reverse('manage_users'))
        created_user = User.objects.filter(email='jane.doe@hospital.org').first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.role, 'PHARMACIST')
        self.assertTrue(created_user.is_staff)

    def test_medication_stock_api(self):
        """Test real-time stock & batch lookup API."""
        response = self.client.get(reverse('medication_stock_api', args=[self.med.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['id'], self.med.id)
        self.assertEqual(data['non_expired_stock'], 400)
        self.assertEqual(len(data['batches']), 2)



    def test_manage_users_view_actions(self):
        """Test Admin role management view actions: role update, edit details, toggle active (suspend), delete user."""
        self.client.login(email='admin@hospital.org', password='Password123!')

        # 1. Role update
        self.client.post(reverse('manage_users'), {
            'action': 'update_role',
            'user_id': self.pharmacist.id,
            'role': 'MANAGER'
        })
        self.pharmacist.refresh_from_db()
        self.assertEqual(self.pharmacist.role, 'MANAGER')

        # 2. Edit User details
        self.client.post(reverse('manage_users'), {
            'action': 'edit_user',
            'user_id': self.pharmacist.id,
            'first_name': 'John',
            'last_name': 'Pharm',
            'email': 'john.pharm@hospital.org',
            'role': 'PHARMACIST'
        })
        self.pharmacist.refresh_from_db()
        self.assertEqual(self.pharmacist.first_name, 'John')
        self.assertEqual(self.pharmacist.email, 'john.pharm@hospital.org')

        # 3. Toggle Active Status (Suspend/Activate)
        self.client.post(reverse('manage_users'), {
            'action': 'toggle_active',
            'user_id': self.pharmacist.id
        })
        self.pharmacist.refresh_from_db()
        self.assertFalse(self.pharmacist.is_active)

        # 4. Delete User
        self.client.post(reverse('manage_users'), {
            'action': 'delete_user',
            'user_id': self.pharmacist.id
        })
        self.assertFalse(User.objects.filter(id=self.pharmacist.id).exists())

    def test_signout_view(self):
        """Test signout route redirects to login."""
        response = self.client.get(reverse('signout'))
        self.assertRedirects(response, reverse('login'))

    def test_multi_item_fefo_cart_and_pos_checkout_naira(self):
        """Test multi-item dispensing with cart system, Nigerian Naira pricing, and payment method selection."""
        # Create second medication with Naira pricing
        med2 = Medication.objects.create(
            name="Paracetamol 500mg", sku="MED-PCM-500", section=self.section, supplier=self.supplier,
            unit="Tablets", unit_cost=50.00, selling_price_per_unit=100.00, annual_demand=12000,
            ordering_cost=500.00, holding_cost=10.00, daily_consumption=40, lead_time_days=5, safety_stock=200, max_level=2500
        )
        today = timezone.now().date()
        MedicationBatch.objects.create(
            medication=med2, supplier=self.supplier, batch_number="PCM-001",
            initial_quantity=500, quantity=500, manufacture_date=today - timedelta(days=10), expiry_date=today + timedelta(days=200)
        )

        # 1. Add Amoxicillin to Cart (150 units -> should consume 100 from batch1 and 50 from batch2)
        res1 = self.client.post(
            reverse('cart_add_item'),
            data=json.dumps({'medication_id': self.med.id, 'quantity': 150}),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()['success'])

        # 2. Add Paracetamol to Cart (200 units @ ₦100 = ₦20,000)
        res2 = self.client.post(
            reverse('cart_add_item'),
            data=json.dumps({'medication_id': med2.id, 'quantity': 200}),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)

        # 3. Check Cart contents
        res_cart = self.client.get(reverse('cart_get_contents'))
        self.assertEqual(res_cart.status_code, 200)
        cart_data = res_cart.json()
        self.assertEqual(cart_data['item_count'], 2)
        self.assertEqual(cart_data['total_units'], 350)
        # Amox selling price default 200.00 * 150 = 30,000; PCM 100.00 * 200 = 20,000 -> Total = 50,000
        expected_total = (150 * float(self.med.selling_price_per_unit)) + (200 * float(med2.selling_price_per_unit))
        self.assertEqual(cart_data['total_naira'], expected_total)

        # 4. Finalize Checkout with POS payment method
        res_checkout = self.client.post(
            reverse('checkout_and_dispense'),
            data=json.dumps({
                'patient_info': 'Chioma Adeleke / Rx #8892',
                'payment_method': 'POS',
                'notes': 'Dispensed with dosage instructions.'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_checkout.status_code, 200)
        checkout_data = res_checkout.json()
        self.assertTrue(checkout_data['success'])
        self.assertEqual(checkout_data['total_amount_naira'], expected_total)
        self.assertEqual(checkout_data['payment_method'], 'POS / Debit Card (₦)')

        # 5. Verify FEFO batch allocation on Amoxicillin
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch1.quantity, 0) # 100 exhausted
        self.assertEqual(self.batch2.quantity, 250) # 300 - 50 = 250

        # 6. Verify Sales Receipt View
        receipt_res = self.client.get(reverse('sales_receipt', args=[checkout_data['transaction_ref']]))
        self.assertEqual(receipt_res.status_code, 200)
        self.assertContains(receipt_res, 'Chioma Adeleke')
        self.assertContains(receipt_res, checkout_data['transaction_ref'])



