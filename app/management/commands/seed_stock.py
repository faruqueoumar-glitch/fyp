import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from app.models import (
    PharmacySection, Supplier, Medication, MedicationBatch,
    PurchaseOrder, PurchaseOrderItem, SalesTransaction, SalesTransactionItem, StockAuditLedger
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds realistic stock and inventory data for all pharmacy sections'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting stock data seeding for all pharmacy sections...'))
        today = timezone.now().date()

        # 1. Ensure Suppliers Exist
        suppliers_data = [
            {
                'name': 'Fidson Healthcare Plc',
                'contact_person': 'Dr. Alabi Williams',
                'email': 'orders@fidson.com',
                'phone': '+234-1-342-9100',
                'address': '26, Kofo Abayomi Street, Victoria Island, Lagos, Nigeria'
            },
            {
                'name': 'May & Baker Nigeria Plc',
                'contact_person': 'Mrs. Chidimma Okeke',
                'email': 'sales@may-baker.com',
                'phone': '+234-1-280-5160',
                'address': '1, May & Baker Avenue, Ikeja, Lagos, Nigeria'
            },
            {
                'name': 'Emzor Pharmaceutical Industries',
                'contact_person': 'Chief Emeka Nnamdi',
                'email': 'supply@emzorpharma.com',
                'phone': '+234-1-460-7000',
                'address': 'Plot 3C, Block E, Isolo Industrial Estate, Lagos, Nigeria'
            },
            {
                'name': 'Swiss Pharma Nigeria Limited (Swipha)',
                'contact_person': 'Pharm. Yusuf Bello',
                'email': 'info@swiphanigeria.com',
                'phone': '+234-1-492-0543',
                'address': '5, Farm Cave Road, Agege Industrial Estate, Lagos, Nigeria'
            },
            {
                'name': 'GlaxoSmithKline Consumer Nigeria',
                'contact_person': 'Pharm. Sarah Johnson',
                'email': 'ng.orders@gsk.com',
                'phone': '+234-1-271-8000',
                'address': '1, Industrial Avenue, Ilupeju, Lagos, Nigeria'
            }
        ]

        suppliers_map = {}
        for s in suppliers_data:
            sup, _ = Supplier.objects.get_or_create(name=s['name'], defaults=s)
            suppliers_map[s['name']] = sup

        # 2. Ensure Sections Exist
        sections_data = [
            {
                'name': 'Main Central Pharmacy',
                'code': 'SEC-MAIN',
                'description': 'Primary inpatient and outpatient central pharmaceutical store.'
            },
            {
                'name': 'Inpatient Ward Dispensary',
                'code': 'SEC-INP',
                'description': 'Dedicated ward medication supply and inpatient prescription processing.'
            },
            {
                'name': 'Outpatient Pharmacy',
                'code': 'SEC-OUTP',
                'description': 'Outpatient prescription fulfillment and ambulatory drug storage.'
            },
            {
                'name': 'Accident & Emergency (A&E) Pharmacy',
                'code': 'SEC-EMERG',
                'description': 'Emergency medicine reserve, critical injectables, and trauma kits.'
            },
            {
                'name': 'Pediatric & Neonatal Pharmacy',
                'code': 'SEC-PED',
                'description': 'Pediatric syrup formulations, dosage adjustments, and neonatal care.'
            },
            {
                'name': 'ICU & Critical Care Pharmacy',
                'code': 'SEC-ICU',
                'description': 'Intensive Care Unit narcotics, high-alert medications, and IV solutions.'
            }
        ]

        sections_map = {}
        for sec in sections_data:
            section_obj, _ = PharmacySection.objects.get_or_create(code=sec['code'], defaults=sec)
            sections_map[sec['code']] = section_obj

        # 3. Comprehensive Inventory Stock Catalog across ALL Sections
        medications_catalog = [
            # SEC-MAIN: Main Central Pharmacy
            {
                'section_code': 'SEC-MAIN',
                'name': 'Amoxicillin 500mg',
                'sku': 'MED-AMX-500',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'Capsules',
                'unit_cost': 150.00,
                'selling_price_per_unit': 250.00,
                'annual_demand': 4800,
                'ordering_cost': 500.00,
                'holding_cost': 20.00,
                'daily_consumption': 15,
                'lead_time_days': 7,
                'safety_stock': 100,
                'max_level': 1000,
                'batches': [
                    {'batch_number': 'BATCH-AMX-2026A', 'qty': 450, 'mfg_days_ago': 60, 'exp_days': 180},
                    {'batch_number': 'BATCH-AMX-2026B', 'qty': 600, 'mfg_days_ago': 20, 'exp_days': 360},
                ]
            },
            {
                'section_code': 'SEC-MAIN',
                'name': 'Artemether/Lumefantrine 80/480mg',
                'sku': 'MED-ACT-80480',
                'supplier_name': 'Swiss Pharma Nigeria Limited (Swipha)',
                'unit': 'Tablets',
                'unit_cost': 800.00,
                'selling_price_per_unit': 1200.00,
                'annual_demand': 3600,
                'ordering_cost': 500.00,
                'holding_cost': 50.00,
                'daily_consumption': 12,
                'lead_time_days': 7,
                'safety_stock': 80,
                'max_level': 800,
                'batches': [
                    {'batch_number': 'BATCH-ACT-001', 'qty': 300, 'mfg_days_ago': 90, 'exp_days': 240},
                    {'batch_number': 'BATCH-ACT-002', 'qty': 500, 'mfg_days_ago': 10, 'exp_days': 400},
                ]
            },
            {
                'section_code': 'SEC-MAIN',
                'name': 'Ciprofloxacin 500mg',
                'sku': 'MED-CIP-500',
                'supplier_name': 'May & Baker Nigeria Plc',
                'unit': 'Tablets',
                'unit_cost': 200.00,
                'selling_price_per_unit': 350.00,
                'annual_demand': 3000,
                'ordering_cost': 500.00,
                'holding_cost': 25.00,
                'daily_consumption': 10,
                'lead_time_days': 7,
                'safety_stock': 60,
                'max_level': 600,
                'batches': [
                    {'batch_number': 'BATCH-CIP-101', 'qty': 250, 'mfg_days_ago': 45, 'exp_days': 300},
                ]
            },
            {
                'section_code': 'SEC-MAIN',
                'name': 'Paracetamol Infusion 100ml',
                'sku': 'MED-PCM-IV100',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'IV Bottles',
                'unit_cost': 650.00,
                'selling_price_per_unit': 1100.00,
                'annual_demand': 2400,
                'ordering_cost': 500.00,
                'holding_cost': 40.00,
                'daily_consumption': 8,
                'lead_time_days': 5,
                'safety_stock': 50,
                'max_level': 400,
                'batches': [
                    {'batch_number': 'BATCH-PCMIV-88', 'qty': 180, 'mfg_days_ago': 30, 'exp_days': 120},
                ]
            },
            {
                'section_code': 'SEC-MAIN',
                'name': 'Ceftriaxone 1g Injection',
                'sku': 'MED-CRO-1G',
                'supplier_name': 'GlaxoSmithKline Consumer Nigeria',
                'unit': 'Vials',
                'unit_cost': 1200.00,
                'selling_price_per_unit': 1850.00,
                'annual_demand': 1800,
                'ordering_cost': 500.00,
                'holding_cost': 60.00,
                'daily_consumption': 6,
                'lead_time_days': 7,
                'safety_stock': 40,
                'max_level': 350,
                'batches': [
                    {'batch_number': 'BATCH-CRO-401', 'qty': 120, 'mfg_days_ago': 50, 'exp_days': 200},
                ]
            },

            # SEC-INP: Inpatient Ward Dispensary
            {
                'section_code': 'SEC-INP',
                'name': 'Tramadol 50mg/ml Inj',
                'sku': 'MED-TRM-50INJ',
                'supplier_name': 'Swiss Pharma Nigeria Limited (Swipha)',
                'unit': 'Ampoules',
                'unit_cost': 350.00,
                'selling_price_per_unit': 600.00,
                'annual_demand': 1500,
                'ordering_cost': 500.00,
                'holding_cost': 30.00,
                'daily_consumption': 5,
                'lead_time_days': 7,
                'safety_stock': 30,
                'max_level': 300,
                'batches': [
                    {'batch_number': 'BATCH-TRM-901', 'qty': 90, 'mfg_days_ago': 120, 'exp_days': 80}, # Warning 90d
                ]
            },
            {
                'section_code': 'SEC-INP',
                'name': 'Normal Saline 0.9% 500ml',
                'sku': 'MED-NS-500',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'IV Bags',
                'unit_cost': 450.00,
                'selling_price_per_unit': 750.00,
                'annual_demand': 6000,
                'ordering_cost': 500.00,
                'holding_cost': 25.00,
                'daily_consumption': 20,
                'lead_time_days': 5,
                'safety_stock': 100,
                'max_level': 1000,
                'batches': [
                    {'batch_number': 'BATCH-NS-771', 'qty': 350, 'mfg_days_ago': 60, 'exp_days': 400},
                    {'batch_number': 'BATCH-NS-772', 'qty': 400, 'mfg_days_ago': 10, 'exp_days': 600},
                ]
            },
            {
                'section_code': 'SEC-INP',
                'name': "Ringer's Lactate 500ml",
                'sku': 'MED-RL-500',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'IV Bags',
                'unit_cost': 500.00,
                'selling_price_per_unit': 850.00,
                'annual_demand': 4000,
                'ordering_cost': 500.00,
                'holding_cost': 30.00,
                'daily_consumption': 14,
                'lead_time_days': 5,
                'safety_stock': 80,
                'max_level': 700,
                'batches': [
                    {'batch_number': 'BATCH-RL-201', 'qty': 280, 'mfg_days_ago': 40, 'exp_days': 350},
                ]
            },
            {
                'section_code': 'SEC-INP',
                'name': 'Diclofenac Sodium 75mg/3ml',
                'sku': 'MED-DIC-75',
                'supplier_name': 'May & Baker Nigeria Plc',
                'unit': 'Ampoules',
                'unit_cost': 180.00,
                'selling_price_per_unit': 350.00,
                'annual_demand': 2000,
                'ordering_cost': 500.00,
                'holding_cost': 20.00,
                'daily_consumption': 8,
                'lead_time_days': 7,
                'safety_stock': 50, # safety_stock 50, rop = (8*7)+50 = 106. current=45 -> BELOW MINIMUM!
                'max_level': 400,
                'batches': [
                    {'batch_number': 'BATCH-DIC-102', 'qty': 45, 'mfg_days_ago': 180, 'exp_days': 25}, # Critical 30d
                ]
            },
            {
                'section_code': 'SEC-INP',
                'name': 'Enoxaparin 40mg Prefilled Syringe',
                'sku': 'MED-ENX-40',
                'supplier_name': 'GlaxoSmithKline Consumer Nigeria',
                'unit': 'Syringes',
                'unit_cost': 3500.00,
                'selling_price_per_unit': 5200.00,
                'annual_demand': 600,
                'ordering_cost': 500.00,
                'holding_cost': 150.00,
                'daily_consumption': 2,
                'lead_time_days': 10,
                'safety_stock': 15,
                'max_level': 120,
                'batches': [
                    {'batch_number': 'BATCH-ENX-05', 'qty': 60, 'mfg_days_ago': 30, 'exp_days': 180},
                ]
            },

            # SEC-OUTP: Outpatient Pharmacy
            {
                'section_code': 'SEC-OUTP',
                'name': 'Paracetamol 500mg',
                'sku': 'MED-PCM-500',
                'supplier_name': 'Emzor Pharmaceutical Industries',
                'unit': 'Tablets',
                'unit_cost': 50.00,
                'selling_price_per_unit': 100.00,
                'annual_demand': 12000,
                'ordering_cost': 500.00,
                'holding_cost': 10.00,
                'daily_consumption': 40,
                'lead_time_days': 5,
                'safety_stock': 200,
                'max_level': 2500,
                'batches': [
                    {'batch_number': 'BATCH-PCM-991', 'qty': 1200, 'mfg_days_ago': 30, 'exp_days': 365},
                ]
            },
            {
                'section_code': 'SEC-OUTP',
                'name': 'Metronidazole 400mg',
                'sku': 'MED-FLG-400',
                'supplier_name': 'Emzor Pharmaceutical Industries',
                'unit': 'Tablets',
                'unit_cost': 60.00,
                'selling_price_per_unit': 120.00,
                'annual_demand': 6000,
                'ordering_cost': 500.00,
                'holding_cost': 12.00,
                'daily_consumption': 20,
                'lead_time_days': 5,
                'safety_stock': 120,
                'max_level': 1200,
                'batches': [
                    {'batch_number': 'BATCH-FLG-501', 'qty': 500, 'mfg_days_ago': 40, 'exp_days': 400},
                ]
            },
            {
                'section_code': 'SEC-OUTP',
                'name': 'Omeprazole 20mg',
                'sku': 'MED-OMP-20',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'Capsules',
                'unit_cost': 180.00,
                'selling_price_per_unit': 300.00,
                'annual_demand': 2400,
                'ordering_cost': 500.00,
                'holding_cost': 30.00,
                'daily_consumption': 8,
                'lead_time_days': 7,
                'safety_stock': 50, # ROP = 106. current = 30 -> BELOW MINIMUM & Critical 30 days
                'max_level': 500,
                'batches': [
                    {'batch_number': 'BATCH-OMP-112', 'qty': 30, 'mfg_days_ago': 200, 'exp_days': 18},
                ]
            },
            {
                'section_code': 'SEC-OUTP',
                'name': 'Amlodipine 5mg',
                'sku': 'MED-AML-5',
                'supplier_name': 'May & Baker Nigeria Plc',
                'unit': 'Tablets',
                'unit_cost': 90.00,
                'selling_price_per_unit': 160.00,
                'annual_demand': 5000,
                'ordering_cost': 500.00,
                'holding_cost': 15.00,
                'daily_consumption': 18,
                'lead_time_days': 7,
                'safety_stock': 100,
                'max_level': 1000,
                'batches': [
                    {'batch_number': 'BATCH-AML-601', 'qty': 650, 'mfg_days_ago': 50, 'exp_days': 450},
                ]
            },
            {
                'section_code': 'SEC-OUTP',
                'name': 'Lisinopril 10mg',
                'sku': 'MED-LIS-10',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'Tablets',
                'unit_cost': 110.00,
                'selling_price_per_unit': 200.00,
                'annual_demand': 3600,
                'ordering_cost': 500.00,
                'holding_cost': 20.00,
                'daily_consumption': 12,
                'lead_time_days': 7,
                'safety_stock': 80,
                'max_level': 800,
                'batches': [
                    {'batch_number': 'BATCH-LIS-401', 'qty': 400, 'mfg_days_ago': 60, 'exp_days': 300},
                ]
            },
            {
                'section_code': 'SEC-OUTP',
                'name': 'Atorvastatin 20mg',
                'sku': 'MED-ATV-20',
                'supplier_name': 'GlaxoSmithKline Consumer Nigeria',
                'unit': 'Tablets',
                'unit_cost': 450.00,
                'selling_price_per_unit': 800.00,
                'annual_demand': 2000,
                'ordering_cost': 500.00,
                'holding_cost': 40.00,
                'daily_consumption': 7,
                'lead_time_days': 7,
                'safety_stock': 50,
                'max_level': 400,
                'batches': [
                    {'batch_number': 'BATCH-ATV-801', 'qty': 220, 'mfg_days_ago': 30, 'exp_days': 250},
                ]
            },

            # SEC-EMERG: Accident & Emergency (A&E) Pharmacy
            {
                'section_code': 'SEC-EMERG',
                'name': 'Adrenaline 1mg/ml Injection',
                'sku': 'MED-ADR-1MG',
                'supplier_name': 'Swiss Pharma Nigeria Limited (Swipha)',
                'unit': 'Ampoules',
                'unit_cost': 750.00,
                'selling_price_per_unit': 1250.00,
                'annual_demand': 1000,
                'ordering_cost': 500.00,
                'holding_cost': 50.00,
                'daily_consumption': 4,
                'lead_time_days': 5,
                'safety_stock': 25,
                'max_level': 200,
                'batches': [
                    {'batch_number': 'BATCH-ADR-01', 'qty': 80, 'mfg_days_ago': 40, 'exp_days': 180},
                ]
            },
            {
                'section_code': 'SEC-EMERG',
                'name': 'Hydrocortisone 100mg Inj',
                'sku': 'MED-HYD-100',
                'supplier_name': 'May & Baker Nigeria Plc',
                'unit': 'Vials',
                'unit_cost': 600.00,
                'selling_price_per_unit': 1000.00,
                'annual_demand': 1200,
                'ordering_cost': 500.00,
                'holding_cost': 40.00,
                'daily_consumption': 5,
                'lead_time_days': 7,
                'safety_stock': 30,
                'max_level': 250,
                'batches': [
                    {'batch_number': 'BATCH-HYD-501', 'qty': 110, 'mfg_days_ago': 50, 'exp_days': 220},
                ]
            },
            {
                'section_code': 'SEC-EMERG',
                'name': 'Atropine Sulfate 1mg/ml Inj',
                'sku': 'MED-ATP-1MG',
                'supplier_name': 'Swiss Pharma Nigeria Limited (Swipha)',
                'unit': 'Ampoules',
                'unit_cost': 400.00,
                'selling_price_per_unit': 700.00,
                'annual_demand': 800,
                'ordering_cost': 500.00,
                'holding_cost': 30.00,
                'daily_consumption': 3,
                'lead_time_days': 7,
                'safety_stock': 20, # current = 0 -> OUT_OF_STOCK & EXPIRED!
                'max_level': 150,
                'batches': [
                    {'batch_number': 'BATCH-ATP-001', 'qty': 0, 'mfg_days_ago': 370, 'exp_days': -10},
                ]
            },
            {
                'section_code': 'SEC-EMERG',
                'name': 'Snake Venom Antiserum (Polyvalent)',
                'sku': 'MED-SNAKE-AV',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'Vials',
                'unit_cost': 35000.00,
                'selling_price_per_unit': 48000.00,
                'annual_demand': 100,
                'ordering_cost': 1000.00,
                'holding_cost': 1500.00,
                'daily_consumption': 1,
                'lead_time_days': 14,
                'safety_stock': 5,
                'max_level': 30,
                'batches': [
                    {'batch_number': 'BATCH-AV-2026', 'qty': 15, 'mfg_days_ago': 60, 'exp_days': 300},
                ]
            },
            {
                'section_code': 'SEC-EMERG',
                'name': 'Diazepam 10mg/2ml Inj',
                'sku': 'MED-DZP-10',
                'supplier_name': 'Emzor Pharmaceutical Industries',
                'unit': 'Ampoules',
                'unit_cost': 250.00,
                'selling_price_per_unit': 450.00,
                'annual_demand': 1500,
                'ordering_cost': 500.00,
                'holding_cost': 25.00,
                'daily_consumption': 5,
                'lead_time_days': 5,
                'safety_stock': 30,
                'max_level': 200,
                'batches': [
                    {'batch_number': 'BATCH-DZP-12', 'qty': 95, 'mfg_days_ago': 45, 'exp_days': 150},
                ]
            },

            # SEC-PED: Pediatric & Neonatal Pharmacy
            {
                'section_code': 'SEC-PED',
                'name': 'Paracetamol Syrup 120mg/5ml',
                'sku': 'MED-PED-PCM',
                'supplier_name': 'Emzor Pharmaceutical Industries',
                'unit': 'Bottles 60ml',
                'unit_cost': 350.00,
                'selling_price_per_unit': 600.00,
                'annual_demand': 3000,
                'ordering_cost': 500.00,
                'holding_cost': 20.00,
                'daily_consumption': 10,
                'lead_time_days': 5,
                'safety_stock': 50,
                'max_level': 400,
                'batches': [
                    {'batch_number': 'BATCH-PEDPCM-01', 'qty': 200, 'mfg_days_ago': 40, 'exp_days': 280},
                ]
            },
            {
                'section_code': 'SEC-PED',
                'name': 'Amoxicillin Oral Susp 125mg/5ml',
                'sku': 'MED-PED-AMX',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'Bottles 100ml',
                'unit_cost': 550.00,
                'selling_price_per_unit': 950.00,
                'annual_demand': 2000,
                'ordering_cost': 500.00,
                'holding_cost': 30.00,
                'daily_consumption': 7,
                'lead_time_days': 7,
                'safety_stock': 40,
                'max_level': 300,
                'batches': [
                    {'batch_number': 'BATCH-PEDAMX-02', 'qty': 150, 'mfg_days_ago': 50, 'exp_days': 150},
                ]
            },
            {
                'section_code': 'SEC-PED',
                'name': 'Zinc Sulfate 20mg Dispersible',
                'sku': 'MED-ZNC-20',
                'supplier_name': 'May & Baker Nigeria Plc',
                'unit': 'Blisters',
                'unit_cost': 120.00,
                'selling_price_per_unit': 220.00,
                'annual_demand': 4000,
                'ordering_cost': 500.00,
                'holding_cost': 15.00,
                'daily_consumption': 12,
                'lead_time_days': 5,
                'safety_stock': 60,
                'max_level': 600,
                'batches': [
                    {'batch_number': 'BATCH-ZNC-99', 'qty': 400, 'mfg_days_ago': 30, 'exp_days': 500},
                ]
            },
            {
                'section_code': 'SEC-PED',
                'name': 'ORS (Oral Rehydration Salts)',
                'sku': 'MED-ORS-SAC',
                'supplier_name': 'Emzor Pharmaceutical Industries',
                'unit': 'Sachets',
                'unit_cost': 80.00,
                'selling_price_per_unit': 150.00,
                'annual_demand': 8000,
                'ordering_cost': 500.00,
                'holding_cost': 10.00,
                'daily_consumption': 25,
                'lead_time_days': 5,
                'safety_stock': 150,
                'max_level': 1500,
                'batches': [
                    {'batch_number': 'BATCH-ORS-101', 'qty': 750, 'mfg_days_ago': 20, 'exp_days': 600},
                ]
            },
            {
                'section_code': 'SEC-PED',
                'name': 'Ibuprofen Suspension 100mg/5ml',
                'sku': 'MED-PED-IBU',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'Bottles 100ml',
                'unit_cost': 480.00,
                'selling_price_per_unit': 800.00,
                'annual_demand': 1800,
                'ordering_cost': 500.00,
                'holding_cost': 25.00,
                'daily_consumption': 6,
                'lead_time_days': 7,
                'safety_stock': 40,
                'max_level': 300,
                'batches': [
                    {'batch_number': 'BATCH-PEDIBU-05', 'qty': 130, 'mfg_days_ago': 45, 'exp_days': 210},
                ]
            },

            # SEC-ICU: ICU & Critical Care Pharmacy
            {
                'section_code': 'SEC-ICU',
                'name': 'Propofol 1% 20ml Emulsion',
                'sku': 'MED-PPF-20ML',
                'supplier_name': 'Swiss Pharma Nigeria Limited (Swipha)',
                'unit': 'Vials',
                'unit_cost': 2800.00,
                'selling_price_per_unit': 4500.00,
                'annual_demand': 800,
                'ordering_cost': 500.00,
                'holding_cost': 120.00,
                'daily_consumption': 3,
                'lead_time_days': 7,
                'safety_stock': 20,
                'max_level': 150,
                'batches': [
                    {'batch_number': 'BATCH-PPF-88', 'qty': 70, 'mfg_days_ago': 30, 'exp_days': 120},
                ]
            },
            {
                'section_code': 'SEC-ICU',
                'name': 'Noradrenaline (Norepinephrine) 4mg',
                'sku': 'MED-NOR-4MG',
                'supplier_name': 'GlaxoSmithKline Consumer Nigeria',
                'unit': 'Ampoules',
                'unit_cost': 4200.00,
                'selling_price_per_unit': 6800.00,
                'annual_demand': 600,
                'ordering_cost': 500.00,
                'holding_cost': 150.00,
                'daily_consumption': 2,
                'lead_time_days': 7,
                'safety_stock': 15,
                'max_level': 100,
                'batches': [
                    {'batch_number': 'BATCH-NOR-301', 'qty': 40, 'mfg_days_ago': 40, 'exp_days': 90},
                ]
            },
            {
                'section_code': 'SEC-ICU',
                'name': 'Fentanyl 100mcg/2ml Inj',
                'sku': 'MED-FNT-100',
                'supplier_name': 'Swiss Pharma Nigeria Limited (Swipha)',
                'unit': 'Ampoules',
                'unit_cost': 3800.00,
                'selling_price_per_unit': 6000.00,
                'annual_demand': 400,
                'ordering_cost': 500.00,
                'holding_cost': 130.00,
                'daily_consumption': 2,
                'lead_time_days': 10,
                'safety_stock': 10,
                'max_level': 80,
                'batches': [
                    {'batch_number': 'BATCH-FNT-09', 'qty': 25, 'mfg_days_ago': 60, 'exp_days': 140},
                ]
            },
            {
                'section_code': 'SEC-ICU',
                'name': 'Meropenem 1g Powder Inj',
                'sku': 'MED-MRP-1G',
                'supplier_name': 'Fidson Healthcare Plc',
                'unit': 'Vials',
                'unit_cost': 5500.00,
                'selling_price_per_unit': 8500.00,
                'annual_demand': 900,
                'ordering_cost': 500.00,
                'holding_cost': 200.00,
                'daily_consumption': 3,
                'lead_time_days': 7,
                'safety_stock': 25,
                'max_level': 180,
                'batches': [
                    {'batch_number': 'BATCH-MRP-501', 'qty': 85, 'mfg_days_ago': 30, 'exp_days': 240},
                ]
            },
            {
                'section_code': 'SEC-ICU',
                'name': 'Vancomycin 500mg Injection',
                'sku': 'MED-VAN-500',
                'supplier_name': 'GlaxoSmithKline Consumer Nigeria',
                'unit': 'Vials',
                'unit_cost': 4000.00,
                'selling_price_per_unit': 6500.00,
                'annual_demand': 500,
                'ordering_cost': 500.00,
                'holding_cost': 140.00,
                'daily_consumption': 2,
                'lead_time_days': 7,
                'safety_stock': 15,
                'max_level': 100,
                'batches': [
                    {'batch_number': 'BATCH-VAN-202', 'qty': 50, 'mfg_days_ago': 50, 'exp_days': 190},
                ]
            },
        ]

        created_med_count = 0
        created_batch_count = 0

        for item in medications_catalog:
            section_obj = sections_map.get(item['section_code'])
            supplier_obj = suppliers_map.get(item['supplier_name'])

            med_obj, created = Medication.objects.get_or_create(
                sku=item['sku'],
                defaults={
                    'name': item['name'],
                    'section': section_obj,
                    'supplier': supplier_obj,
                    'unit': item['unit'],
                    'unit_cost': item['unit_cost'],
                    'selling_price_per_unit': item['selling_price_per_unit'],
                    'annual_demand': item['annual_demand'],
                    'ordering_cost': item['ordering_cost'],
                    'holding_cost': item['holding_cost'],
                    'daily_consumption': item['daily_consumption'],
                    'lead_time_days': item['lead_time_days'],
                    'safety_stock': item['safety_stock'],
                    'max_level': item['max_level'],
                }
            )

            # Update fields if existing
            if not created:
                med_obj.section = section_obj
                med_obj.supplier = supplier_obj
                med_obj.unit_cost = item['unit_cost']
                med_obj.selling_price_per_unit = item['selling_price_per_unit']
                med_obj.save()
            else:
                created_med_count += 1

            # Seed Medication Batches
            for b_info in item['batches']:
                mfg_date = today - timedelta(days=b_info['mfg_days_ago'])
                exp_date = today + timedelta(days=b_info['exp_days'])
                
                batch_obj, b_created = MedicationBatch.objects.get_or_create(
                    medication=med_obj,
                    batch_number=b_info['batch_number'],
                    defaults={
                        'supplier': supplier_obj,
                        'initial_quantity': b_info['qty'],
                        'quantity': b_info['qty'],
                        'manufacture_date': mfg_date,
                        'expiry_date': exp_date,
                        'received_date': timezone.now() - timedelta(days=b_info['mfg_days_ago'])
                    }
                )
                if b_created:
                    created_batch_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_med_count} medications and {created_batch_count} stock batches across all {len(sections_map)} pharmacy sections."))

        # 4. Seed Purchase Orders for demonstration
        staff_user = User.objects.filter(role__in=['ADMIN', 'MANAGER']).first()
        if PurchaseOrder.objects.count() == 0 and staff_user:
            po1 = PurchaseOrder.objects.create(
                supplier=suppliers_map['Fidson Healthcare Plc'],
                created_by=staff_user,
                status='APPROVED',
                notes='Monthly replenishment for Main Pharmacy & Inpatient ward.'
            )
            med_amx = Medication.objects.filter(sku='MED-AMX-500').first()
            if med_amx:
                PurchaseOrderItem.objects.create(
                    purchase_order=po1,
                    medication=med_amx,
                    quantity_ordered=med_amx.eoq,
                    eoq_recommended_qty=med_amx.eoq,
                    unit_price=med_amx.unit_cost
                )

            po2 = PurchaseOrder.objects.create(
                supplier=suppliers_map['Swiss Pharma Nigeria Limited (Swipha)'],
                created_by=staff_user,
                status='DRAFT',
                notes='FR4 Automated ROP Trigger for Emergency & ICU injectables.'
            )
            med_adr = Medication.objects.filter(sku='MED-ADR-1MG').first()
            if med_adr:
                PurchaseOrderItem.objects.create(
                    purchase_order=po2,
                    medication=med_adr,
                    quantity_ordered=med_adr.eoq,
                    eoq_recommended_qty=med_adr.eoq,
                    unit_price=med_adr.unit_cost
                )

        # 5. Seed Sales Transactions for demonstration
        pharma_user = User.objects.filter(role__in=['PHARMACIST', 'ADMIN']).first()
        if SalesTransaction.objects.count() == 0 and pharma_user:
            med_pcm = Medication.objects.filter(sku='MED-PCM-500').first()
            med_amx = Medication.objects.filter(sku='MED-AMX-500').first()

            if med_pcm and med_amx:
                tx1 = SalesTransaction.objects.create(
                    pharmacist=pharma_user,
                    total_amount_naira=3500.00,
                    payment_method='POS_CARD',
                    patient_info='Outpatient - Prescription #RX-88210',
                    notes='Dispensed via FEFO'
                )
                SalesTransactionItem.objects.create(
                    sales_transaction=tx1,
                    medication=med_pcm,
                    quantity_sold=10,
                    unit_price_naira=med_pcm.selling_price_per_unit
                )
                SalesTransactionItem.objects.create(
                    sales_transaction=tx1,
                    medication=med_amx,
                    quantity_sold=10,
                    unit_price_naira=med_amx.selling_price_per_unit
                )

        self.stdout.write(self.style.SUCCESS("Database now contains rich stock and transaction data for all sections!"))
