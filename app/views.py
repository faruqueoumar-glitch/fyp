import csv
import json
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    LoginForm, RegisterForm, MedicationForm, GoodsReceiptForm,
    FEFODispenseForm, StockAdjustmentForm, PurchaseOrderForm, SupplierForm
)
from .models import (
    PharmacySection, Medication, MedicationBatch, StockAuditLedger,
    Supplier, PurchaseOrder, PurchaseOrderItem
)

User = get_user_model()


def log_audit_trail(request, action_type, affected_entity, entity_pk, before_data, after_data, reason=""):
    """FR2: Helper function to record immutable audit trail entries."""
    user_id = request.user.email if (request and request.user and request.user.is_authenticated) else "system"
    ip = request.META.get('REMOTE_ADDR') if request else None
    
    StockAuditLedger.objects.create(
        user_identity=user_id,
        action_type=action_type,
        affected_entity=affected_entity,
        entity_pk=str(entity_pk),
        before_data=json.dumps(before_data, default=str),
        after_data=json.dumps(after_data, default=str),
        ip_address=ip,
        reason=reason
    )


def calculate_abc_classification():
    """FR6: Calculates ABC Classification based on Annual Consumption Value."""
    meds = list(Medication.objects.all())
    if not meds:
        return []

    # Sort descending by annual consumption value
    meds.sort(key=lambda m: m.annual_consumption_value, reverse=True)
    total_value = sum(m.annual_consumption_value for m in meds)

    cum_value = 0
    results = []
    for m in meds:
        val = m.annual_consumption_value
        prev_pct = (cum_value / total_value * 100) if total_value > 0 else 0
        cum_value += val
        cum_pct = (cum_value / total_value * 100) if total_value > 0 else 0

        # Lorenz curve ABC categorization:
        # Items starting within top 75% value -> Category A
        # Items starting between 75% and 90% -> Category B
        # Remaining items -> Category C
        if prev_pct < 75:
            category = 'A'
        elif prev_pct < 90:
            category = 'B'
        else:
            category = 'C'

        results.append({
            'medication': m,
            'annual_value': val,
            'cum_value': cum_value,
            'cum_pct': round(cum_pct, 1),
            'category': category
        })
    return results



def seed_demo_data_if_empty():
    """Helper to seed initial demo data if database is fresh."""
    if PharmacySection.objects.count() == 0:
        sec1 = PharmacySection.objects.create(name="Central Depot Store", code="DEPOT-01")
        sec2 = PharmacySection.objects.create(name="Outpatient Pharmacy Clinic", code="OUTPAT-01")
        sec3 = PharmacySection.objects.create(name="Inpatient Ward Pharmacy", code="INPAT-01")

        sup1 = Supplier.objects.create(name="PharmaCore Global Ltd", contact_person="Sarah Jenkins", email="orders@pharmacore.com", phone="+1-800-555-0199")
        sup2 = Supplier.objects.create(name="Apex Medical Supplies", contact_person="David Miller", email="supply@apexmed.com", phone="+1-800-555-0244")

        # Create Medications with EOQ & ROP configuration
        m1 = Medication.objects.create(
            name="Amoxicillin 500mg Capsule", sku="MED-AMX-500", section=sec2, supplier=sup1,
            unit="Capsules", unit_cost=4.50, annual_demand=3600, ordering_cost=40.00, holding_cost=1.50,
            daily_consumption=25, lead_time_days=7, safety_stock=50, max_level=600
        )
        m2 = Medication.objects.create(
            name="Metformin 850mg Tablet", sku="MED-MET-850", section=sec1, supplier=sup1,
            unit="Tablets", unit_cost=2.20, annual_demand=5000, ordering_cost=30.00, holding_cost=1.00,
            daily_consumption=35, lead_time_days=5, safety_stock=80, max_level=1000
        )
        m3 = Medication.objects.create(
            name="Insulin Glargine 100IU/ml Vial", sku="MED-INS-100", section=sec3, supplier=sup2,
            unit="Vials", unit_cost=45.00, annual_demand=600, ordering_cost=100.00, holding_cost=8.00,
            daily_consumption=5, lead_time_days=10, safety_stock=20, max_level=150
        )
        m4 = Medication.objects.create(
            name="Paracetamol 500mg Tablet", sku="MED-PCM-500", section=sec2, supplier=sup2,
            unit="Tablets", unit_cost=0.50, annual_demand=12000, ordering_cost=20.00, holding_cost=0.20,
            daily_consumption=80, lead_time_days=3, safety_stock=200, max_level=3000
        )

        today = timezone.now().date()
        MedicationBatch.objects.create(medication=m1, supplier=sup1, batch_number="BAT-AMX-01", initial_quantity=400, quantity=180, manufacture_date=today - timedelta(days=90), expiry_date=today + timedelta(days=25))
        MedicationBatch.objects.create(medication=m1, supplier=sup1, batch_number="BAT-AMX-02", initial_quantity=300, quantity=300, manufacture_date=today - timedelta(days=30), expiry_date=today + timedelta(days=180))
        
        MedicationBatch.objects.create(medication=m2, supplier=sup1, batch_number="BAT-MET-OLD", initial_quantity=100, quantity=40, manufacture_date=today - timedelta(days=400), expiry_date=today - timedelta(days=5)) # Expired
        MedicationBatch.objects.create(medication=m2, supplier=sup1, batch_number="BAT-MET-NEW", initial_quantity=500, quantity=500, manufacture_date=today - timedelta(days=40), expiry_date=today + timedelta(days=120))

        MedicationBatch.objects.create(medication=m3, supplier=sup2, batch_number="BAT-INS-01", initial_quantity=40, quantity=15, manufacture_date=today - timedelta(days=60), expiry_date=today + timedelta(days=60))

        # Initial audit log
        log_audit_trail(None, 'CONFIG_CHANGE', 'System', 1, {}, {'status': 'Demo data initialized'}, 'System setup completed')


# Auth Views
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            log_audit_trail(request, 'USER_LOGIN', 'User', user.id, {}, {'user': user.email, 'role': user.role}, 'User session initiated')
            messages.success(request, f"Welcome back, {user.first_name or user.email} [{user.get_role_display()}].")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email address or password.")

    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        login(request, user)
        log_audit_trail(request, 'USER_LOGIN', 'User', user.id, {}, {'user': user.email, 'role': user.role}, 'New user account registered')
        messages.success(request, f"Account registered successfully as {user.get_role_display()}.")
        return redirect('dashboard')

    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_audit_trail(request, 'USER_LOGIN', 'User', request.user.id, {}, {'user': request.user.email}, 'User logged out')
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect('login')


# FR1 & Dashboard View
@login_required
def dashboard_view(request):
    seed_demo_data_if_empty()
    medications = Medication.objects.all()

    # FR1: Stock Status Counters
    adequate_count = 0
    at_rop_count = 0
    below_min_count = 0
    out_of_stock_count = 0

    rop_alerts = []
    for med in medications:
        status = med.stock_status
        if status == 'OUT_OF_STOCK':
            out_of_stock_count += 1
        elif status == 'BELOW_MINIMUM':
            below_min_count += 1
        elif status == 'AT_REORDER_POINT':
            at_rop_count += 1
        else:
            adequate_count += 1

        if med.current_stock <= med.reorder_point:
            rop_alerts.append(med)

    # FR6: ABC Classification Summary
    abc_summary = calculate_abc_classification()
    abc_counts = {
        'A': sum(1 for item in abc_summary if item['category'] == 'A'),
        'B': sum(1 for item in abc_summary if item['category'] == 'B'),
        'C': sum(1 for item in abc_summary if item['category'] == 'C'),
    }

    # FR7: Expiry Monitoring Alert Module
    today = timezone.now().date()
    expired_batches = MedicationBatch.objects.filter(quantity__gt=0, expiry_date__lte=today).order_by('expiry_date')
    critical_30_batches = MedicationBatch.objects.filter(quantity__gt=0, expiry_date__gt=today, expiry_date__lte=today + timedelta(days=30)).order_by('expiry_date')
    warning_90_batches = MedicationBatch.objects.filter(quantity__gt=0, expiry_date__gt=today + timedelta(days=30), expiry_date__lte=today + timedelta(days=90)).order_by('expiry_date')

    # Audit Trail Integrity Check
    recent_audits = StockAuditLedger.objects.all()[:6]
    ledger_intact = all(item.verify_integrity() for item in recent_audits) if recent_audits else True

    context = {
        'total_medications': len(medications),
        'adequate_count': adequate_count,
        'at_rop_count': at_rop_count,
        'below_min_count': below_min_count,
        'out_of_stock_count': out_of_stock_count,
        'rop_alerts': rop_alerts,
        'abc_counts': abc_counts,
        'expired_batches': expired_batches,
        'critical_30_batches': critical_30_batches,
        'warning_90_batches': warning_90_batches,
        'recent_audits': recent_audits,
        'ledger_intact': ledger_intact,
    }
    return render(request, 'dashboard.html', context)


# 3.2.2.1 Goods Receipt Intake View
@login_required
def receive_batch_view(request):
    """Capturing drug identity, supplier, batch number, manufacture date, expiry date, and quantity received."""
    form = GoodsReceiptForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        batch = form.save(commit=False)
        batch.quantity = batch.initial_quantity
        batch.save()

        # Update drug aggregate balance & log audit record
        med = batch.medication
        log_audit_trail(
            request,
            'STOCK_RECEIPT',
            'MedicationBatch',
            batch.id,
            {'medication': med.name, 'previous_stock': med.current_stock - batch.quantity},
            {'medication': med.name, 'batch_number': batch.batch_number, 'received_qty': batch.quantity, 'new_stock': med.current_stock},
            f"Goods Receipt intake: Batch {batch.batch_number} received from {batch.supplier.name if batch.supplier else 'N/A'}"
        )
        messages.success(request, f"Goods Receipt committed! Batch {batch.batch_number} ({batch.quantity} {med.unit}) added for {med.name}.")
        return redirect('medications_list')

    return render(request, 'inventory/receive_batch.html', {'form': form})


# FR5: FEFO Dispensing Logic
@login_required
def fefo_dispense_view(request):
    """Enforces FEFO dispensing logic at point of transaction."""
    med_id = request.GET.get('medication')
    initial_data = {}
    if med_id:
        initial_data['medication'] = med_id

    form = FEFODispenseForm(request.POST or None, initial=initial_data)
    if request.method == 'POST' and form.is_valid():
        medication = form.cleaned_data['medication']
        quantity_to_dispense = form.cleaned_data['quantity']
        reason = form.cleaned_data.get('reason') or "Patient Prescription FEFO Dispense"

        today = timezone.now().date()
        # FEFO: Active non-expired batches ordered by earliest expiry date first
        active_batches = medication.batches.filter(quantity__gt=0, expiry_date__gt=today).order_by('expiry_date')

        total_available = sum(b.quantity for b in active_batches)
        if quantity_to_dispense > total_available:
            messages.error(request, f"Cannot dispense {quantity_to_dispense} units. Only {total_available} non-expired units available.")
            return render(request, 'inventory/fefo_dispense.html', {'form': form})

        remaining_needed = quantity_to_dispense
        dispensed_details = []

        with transaction.atomic():
            before_stock = medication.current_stock
            for batch in active_batches:
                if remaining_needed <= 0:
                    break

                deduct = min(batch.quantity, remaining_needed)
                batch.quantity -= deduct
                batch.save()
                remaining_needed -= deduct

                dispensed_details.append(f"Batch {batch.batch_number} (Exp: {batch.expiry_date}): {deduct} units")

            after_stock = medication.current_stock

            log_audit_trail(
                request,
                'DISPENSE_FEFO',
                'Medication',
                medication.id,
                {'stock': before_stock},
                {'stock': after_stock, 'dispensed_qty': quantity_to_dispense, 'batches': dispensed_details},
                reason
            )

        details_str = " | ".join(dispensed_details)
        messages.success(request, f"FEFO Dispense Successful! {quantity_to_dispense} {medication.unit} dispensed. Batches used: {details_str}")
        return redirect('medications_list')

    return render(request, 'inventory/fefo_dispense.html', {'form': form})


# Physical Stock Count Adjustment View
@login_required
def stock_adjustment_view(request):
    form = StockAdjustmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        medication = form.cleaned_data['medication']
        actual_count = form.cleaned_data['actual_physical_count']
        reason = form.cleaned_data['reason']

        current = medication.current_stock
        diff = actual_count - current

        if diff != 0:
            # Adjust latest batch or create physical adjustment batch
            today = timezone.now().date()
            latest_batch = medication.batches.filter(expiry_date__gt=today).last()
            if latest_batch:
                latest_batch.quantity = max(0, latest_batch.quantity + diff)
                latest_batch.save()

            log_audit_trail(
                request,
                'STOCK_ADJUSTMENT',
                'Medication',
                medication.id,
                {'system_stock': current},
                {'adjusted_stock': actual_count, 'variance': diff},
                f"Physical Audit Adjustment: {reason}"
            )
            messages.success(request, f"Physical Stock Count adjusted for {medication.name}. Variance: {diff} units.")
        else:
            messages.info(request, "No stock variance detected between system stock and physical count.")

        return redirect('medications_list')

    return render(request, 'inventory/stock_adjustment.html', {'form': form})


# Medications Catalog & ROP / EOQ Optimization View
@login_required
def medications_list_view(request):
    query = request.GET.get('q', '')
    section_id = request.GET.get('section', '')

    medications = Medication.objects.all()
    if query:
        medications = medications.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    if section_id:
        medications = medications.filter(section_id=section_id)

    sections = PharmacySection.objects.all()
    suppliers = Supplier.objects.all()
    med_form = MedicationForm()

    context = {
        'medications': medications,
        'sections': sections,
        'suppliers': suppliers,
        'form': med_form,
        'query': query,
        'selected_section': section_id,
    }
    return render(request, 'medications/list.html', context)


@login_required
def add_medication_view(request):
    form = MedicationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        med = form.save()
        log_audit_trail(request, 'CONFIG_CHANGE', 'Medication', med.id, {}, {'name': med.name, 'sku': med.sku}, 'New Drug Registered')
        messages.success(request, f"Medication '{med.name}' registered with computed ROP: {med.reorder_point} and EOQ: {med.eoq}.")
    return redirect('medications_list')


# FR3 & FR4: Purchase Orders & Automated Draft PO Generation
@login_required
def purchase_orders_view(request):
    orders = PurchaseOrder.objects.all()
    form = PurchaseOrderForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        supplier = form.cleaned_data['supplier']
        medication = form.cleaned_data['medication']
        quantity = form.cleaned_data['quantity']
        notes = form.cleaned_data.get('notes', '')

        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                supplier=supplier,
                created_by=request.user,
                status='DRAFT',
                notes=notes
            )
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                medication=medication,
                quantity_ordered=quantity,
                eoq_recommended_qty=medication.eoq,
                unit_price=medication.unit_cost
            )
            log_audit_trail(request, 'PO_CREATE', 'PurchaseOrder', po.id, {}, {'po_number': po.po_number, 'supplier': supplier.name}, f"Purchase Order Draft Created with EOQ recommendation: {medication.eoq}")

        messages.success(request, f"Purchase Order {po.po_number} created as DRAFT.")
        return redirect('purchase_orders')

    context = {
        'orders': orders,
        'form': form,
    }
    return render(request, 'orders/purchase_orders.html', context)


@login_required
def auto_generate_draft_po_view(request, medication_id):
    """FR4: Automatically generates a draft purchase order using supplier and EOQ guidance."""
    med = get_object_or_404(Medication, id=medication_id)
    if not med.supplier:
        messages.error(request, f"No supplier configured for {med.name}. Please select a supplier first.")
        return redirect('medications_list')

    eoq_qty = med.eoq
    po = PurchaseOrder.objects.create(
        supplier=med.supplier,
        created_by=request.user,
        status='DRAFT',
        notes=f"FR4 Automated ROP Trigger: Stock ({med.current_stock}) <= ROP ({med.reorder_point}). EOQ Recommended: {eoq_qty}"
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        medication=med,
        quantity_ordered=eoq_qty,
        eoq_recommended_qty=eoq_qty,
        unit_price=med.unit_cost
    )
    log_audit_trail(request, 'PO_CREATE', 'PurchaseOrder', po.id, {}, {'po_number': po.po_number, 'medication': med.name}, 'Automated ROP Draft PO Generation')
    messages.success(request, f"Draft Purchase Order {po.po_number} generated for {med.name} with EOQ quantity {eoq_qty}!")
    return redirect('purchase_orders')


@login_required
def approve_po_view(request, po_id):
    if not request.user.is_manager:
        messages.error(request, "Only Manager or Administrator roles can approve purchase orders.")
        return redirect('purchase_orders')

    po = get_object_or_404(PurchaseOrder, id=po_id)
    po.status = 'APPROVED'
    po.save()
    log_audit_trail(request, 'PO_APPROVE', 'PurchaseOrder', po.id, {'status': 'DRAFT'}, {'status': 'APPROVED'}, 'PO Manager Approval')
    messages.success(request, f"Purchase Order {po.po_number} Approved.")
    return redirect('purchase_orders')


# FR6: ABC Classification Console View
@login_required
def abc_classification_view(request):
    abc_data = calculate_abc_classification()
    context = {
        'abc_data': abc_data,
    }
    return render(request, 'analytics/abc_classification.html', context)


# FR7: Expiry Monitoring & Quarantine View
@login_required
def expiries_monitoring_view(request):
    status_filter = request.GET.get('status', '')
    today = timezone.now().date()
    batches = MedicationBatch.objects.all().order_by('expiry_date')

    if status_filter == 'EXPIRED':
        batches = batches.filter(expiry_date__lte=today)
    elif status_filter == '30_DAYS':
        batches = batches.filter(expiry_date__gt=today, expiry_date__lte=today + timedelta(days=30))
    elif status_filter == '90_DAYS':
        batches = batches.filter(expiry_date__gt=today, expiry_date__lte=today + timedelta(days=90))

    context = {
        'batches': batches,
        'status_filter': status_filter,
    }
    return render(request, 'inventory/expiries.html', context)


@login_required
def quarantine_batch_view(request, batch_id):
    batch = get_object_or_404(MedicationBatch, id=batch_id)
    before_qty = batch.quantity
    batch.quantity = 0
    batch.save()

    log_audit_trail(
        request,
        'QUARANTINE',
        'MedicationBatch',
        batch.id,
        {'quantity': before_qty},
        {'quantity': 0},
        f"Batch Quarantine: Batch {batch.batch_number} isolated (Expired: {batch.expiry_date})"
    )
    messages.warning(request, f"Batch {batch.batch_number} for {batch.medication.name} has been quarantined.")
    return redirect('expiries_monitoring')


# FR2: Immutable Audit Ledger View
@login_required
def stock_audit_ledger_view(request):
    action_filter = request.GET.get('action', '')
    audits = StockAuditLedger.objects.all()

    if action_filter:
        audits = audits.filter(action_type=action_filter)

    verified_logs = []
    all_intact = True
    for log in audits:
        valid = log.verify_integrity()
        if not valid:
            all_intact = False
        verified_logs.append({'log': log, 'is_valid': valid})

    context = {
        'verified_logs': verified_logs,
        'all_intact': all_intact,
        'action_choices': StockAuditLedger.ACTION_TYPES,
        'action_filter': action_filter,
    }
    return render(request, 'audit/ledger.html', context)


# FR9: Comprehensive Reporting Console & Export Engine
@login_required
def reports_view(request):
    report_type = request.GET.get('type', 'stock_status')
    medications = Medication.objects.all()

    context = {
        'report_type': report_type,
        'medications': medications,
        'abc_data': calculate_abc_classification(),
        'orders': PurchaseOrder.objects.all(),
        'audits': StockAuditLedger.objects.all()[:50],
        'expiries': MedicationBatch.objects.filter(expiry_date__lte=timezone.now().date() + timedelta(days=90)),
    }
    return render(request, 'reports/reports.html', context)


@login_required
def export_report_csv(request):
    """FR9: Exports requested report in CSV format."""
    report_type = request.GET.get('type', 'stock_status')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="pharma_{report_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
    writer = csv.writer(response)

    if report_type == 'stock_status':
        writer.writerow(['SKU', 'Medication Name', 'Section', 'Current Stock', 'Reorder Point (ROP)', 'Min Stock', 'Max Stock', 'EOQ Recommended', 'Status'])
        for med in Medication.objects.all():
            writer.writerow([med.sku, med.name, med.section.name, med.current_stock, med.reorder_point, med.min_level, med.max_level, med.eoq, med.stock_status])

    elif report_type == 'abc_classification':
        writer.writerow(['SKU', 'Medication Name', 'Annual Demand', 'Unit Cost ($)', 'Annual Consumption Value ($)', 'Cumulative %', 'ABC Category'])
        abc_list = calculate_abc_classification()
        for item in abc_list:
            m = item['medication']
            writer.writerow([m.sku, m.name, m.annual_demand, m.unit_cost, item['annual_value'], item['cum_pct'], item['category']])

    elif report_type == 'expiries':
        writer.writerow(['Medication', 'Batch Number', 'Supplier', 'Quantity', 'Expiry Date', 'Days to Expiry', 'Status'])
        for b in MedicationBatch.objects.all():
            writer.writerow([b.medication.name, b.batch_number, b.supplier.name if b.supplier else 'N/A', b.quantity, b.expiry_date, b.days_to_expiry, b.expiry_status])

    elif report_type == 'audit_trail':
        writer.writerow(['Transaction ID', 'Timestamp', 'User', 'Action Type', 'Affected Entity', 'Entity PK', 'IP Address', 'SHA256 Hash'])
        for a in StockAuditLedger.objects.all():
            writer.writerow([a.transaction_id, a.timestamp, a.user_identity, a.action_type, a.affected_entity, a.entity_pk, a.ip_address, a.current_hash])

    return response
