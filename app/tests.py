from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
import math

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

        # Trigger auto draft PO
        response = self.client.get(reverse('auto_generate_draft_po', args=[self.med.id]))
        self.assertRedirects(response, reverse('purchase_orders'))

        po = PurchaseOrder.objects.filter(supplier=self.supplier, status='DRAFT').first()
        self.assertIsNotNone(po)
        self.assertEqual(po.items.first().eoq_recommended_qty, self.med.eoq)

    def test_fr5_fefo_dispensing_logic(self):
        """FR5: Dispenses from earliest expiring batch (batch1 expiring in 15 days) first."""
        response = self.client.post(reverse('fefo_dispense'), {
            'medication': self.med.id,
            'quantity': 150,
            'reason': 'FEFO Test Dispense'
        })
        self.assertRedirects(response, reverse('medications_list'))

        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        # Batch 1 had 100 -> reduced to 0
        # Batch 2 had 300 -> reduced by 50 to 250
        self.assertEqual(self.batch1.quantity, 0)
        self.assertEqual(self.batch2.quantity, 250)

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
        """FR9: Exports CSV report"""
        response = self.client.get(reverse('export_report_csv') + '?type=stock_status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, 'Amoxicillin 500mg')
