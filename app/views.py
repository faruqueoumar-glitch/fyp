import csv
from functools import wraps
import json
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Sum, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    LoginForm, RegisterForm, MedicationForm, GoodsReceiptForm,
    FEFODispenseForm, StockAdjustmentForm, PurchaseOrderForm, SupplierForm, PharmacySectionForm
)
from .models import (
    PharmacySection, Medication, MedicationBatch, StockAuditLedger,
    Supplier, PurchaseOrder, PurchaseOrderItem, SalesTransaction, SalesTransactionItem
)
from notifications.notification_services import NotificationService

User = get_user_model()


def require_permission(permission_name):
    """Decorator to explicitly enforce role-based access permissions."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if not request.user.has_permission(permission_name):
                # If AJAX request, return JsonResponse with 403 status
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': f"Access Denied. You do not have the required permission: '{permission_name}'."
                    }, status=403)
                messages.error(
                    request,
                    f"Access Denied. Your role ({request.user.get_role_display()}) does not have permission to access this resource ({permission_name})."
                )
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


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


DEFAULT_SUPPLIERS = [
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

DEFAULT_SECTIONS = [
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

DEFAULT_MEDICATIONS = [
    {
        'name': 'Paracetamol 500mg',
        'sku': 'MED-PCM-500',
        'section_code': 'SEC-OUTP',
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
        'batch_qty': 800,
        'exp_days': 365,
    },
    {
        'name': 'Amoxicillin 500mg',
        'sku': 'MED-AMX-500',
        'section_code': 'SEC-MAIN',
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
        'batch_qty': 450,
        'exp_days': 180,
    },
    {
        'name': 'Artemether/Lumefantrine 80/480mg',
        'sku': 'MED-ACT-80480',
        'section_code': 'SEC-MAIN',
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
        'batch_qty': 300,
        'exp_days': 240,
    },
    {
        'name': 'Ciprofloxacin 500mg',
        'sku': 'MED-CIP-500',
        'section_code': 'SEC-MAIN',
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
        'batch_qty': 250,
        'exp_days': 300,
    },
    {
        'name': 'Metronidazole 400mg',
        'sku': 'MED-FLG-400',
        'section_code': 'SEC-OUTP',
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
        'batch_qty': 500,
        'exp_days': 400,
    },
    {
        'name': 'Omeprazole 20mg',
        'sku': 'MED-OMP-20',
        'section_code': 'SEC-OUTP',
        'supplier_name': 'Fidson Healthcare Plc',
        'unit': 'Capsules',
        'unit_cost': 180.00,
        'selling_price_per_unit': 300.00,
        'annual_demand': 2400,
        'ordering_cost': 500.00,
        'holding_cost': 30.00,
        'daily_consumption': 8,
        'lead_time_days': 7,
        'safety_stock': 50,
        'max_level': 500,
        'batch_qty': 200,
        'exp_days': 210,
    }
]

def ensure_master_defaults():
    if PharmacySection.objects.count() == 0:
        for s in DEFAULT_SECTIONS:
            PharmacySection.objects.get_or_create(code=s['code'], defaults=s)
    if Supplier.objects.count() == 0:
        for sup in DEFAULT_SUPPLIERS:
            Supplier.objects.get_or_create(name=sup['name'], defaults=sup)
    if Medication.objects.count() < 10:
        try:
            from django.core.management import call_command
            call_command('seed_stock')
        except Exception:
            pass
            
    # Normalize legacy low prices to standard Nigerian Naira if any exist below ₦20
    for med in Medication.objects.all():
        updated = False
        if med.unit_cost < 20:
            med.unit_cost = 100.00
            updated = True
        if med.selling_price_per_unit < 50:
            med.selling_price_per_unit = 200.00
            updated = True
        if med.ordering_cost < 100:
            med.ordering_cost = 500.00
            updated = True
        if updated:
            med.save()


# Pharmacy Sections Management View
@require_permission('search_drug_records')
def sections_list_view(request):
    ensure_master_defaults()
    form = PharmacySectionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if not request.user.can_configure_system:
            messages.error(request, "Access denied. You do not have permission to add new pharmacy sections.")
            return redirect('sections_list')
        section = form.save()
        log_audit_trail(request, 'CONFIG_CHANGE', 'PharmacySection', section.id, {}, {'name': section.name, 'code': section.code}, 'New Pharmacy Section Created')
        messages.success(request, f"Pharmacy Section '{section.name}' ({section.code}) created successfully.")
        return redirect('sections_list')

    sections = PharmacySection.objects.all().order_by('name')
    sections_data = []
    
    total_system_skus = 0
    total_system_units = 0
    total_system_valuation = 0.0

    for sec in sections:
        meds = sec.medications.all().select_related('supplier').prefetch_related('batches')
        sec_skus = meds.count()
        sec_units = sum(m.current_stock for m in meds)
        sec_valuation = sum(m.current_stock * float(m.unit_cost) for m in meds)
        
        adequate = sum(1 for m in meds if m.stock_status == 'ADEQUATE')
        at_rop = sum(1 for m in meds if m.stock_status == 'AT_REORDER_POINT')
        below_min = sum(1 for m in meds if m.stock_status == 'BELOW_MINIMUM')
        out_of_stock = sum(1 for m in meds if m.stock_status == 'OUT_OF_STOCK')
        
        total_system_skus += sec_skus
        total_system_units += sec_units
        total_system_valuation += sec_valuation

        sections_data.append({
            'section': sec,
            'medications': meds,
            'skus_count': sec_skus,
            'total_units': sec_units,
            'valuation': sec_valuation,
            'adequate_count': adequate,
            'at_rop_count': at_rop,
            'below_min_count': below_min,
            'out_of_stock_count': out_of_stock,
        })

    context = {
        'sections_data': sections_data,
        'sections': sections,
        'form': form,
        'total_system_skus': total_system_skus,
        'total_system_units': total_system_units,
        'total_system_valuation': total_system_valuation,
    }
    return render(request, 'sections/sections_list.html', context)


# Suppliers Management View
@require_permission('manage_suppliers')
def suppliers_list_view(request):
    ensure_master_defaults()
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        supplier = form.save()
        log_audit_trail(request, 'CONFIG_CHANGE', 'Supplier', supplier.id, {}, {'name': supplier.name}, 'New Supplier Registered')
        messages.success(request, f"Supplier '{supplier.name}' registered successfully.")
        return redirect('suppliers_list')

    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'suppliers/suppliers_list.html', {'suppliers': suppliers, 'form': form})


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
        if request.user.is_admin:
            return redirect('manage_users')
        return redirect('dashboard')
    messages.error(request, "Public account registration is disabled. Staff accounts must be created by a System Administrator.")
    return redirect('login')


def logout_view(request):
    if request.user.is_authenticated:
        log_audit_trail(request, 'USER_LOGIN', 'User', request.user.id, {}, {'user': request.user.email}, 'User logged out')
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect('login')


@require_permission('manage_users')
def manage_users_view(request):
    if not request.user.is_admin:
        messages.error(request, "Access denied. Only Administrators can manage users.")
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_user':
            form = RegisterForm(request.POST)
            if form.is_valid():
                u = form.save(commit=False)
                u.set_password(form.cleaned_data['password'])
                u.is_staff = True
                u.save()
                log_audit_trail(request, 'USER_CREATE', 'User', u.id, {}, {'user': u.email, 'role': u.role}, f"Staff account provisioned by admin: {request.user.email}")
                messages.success(request, f"New staff account '{u.email}' ({u.get_role_display()}) provisioned successfully.")
            else:
                for field, errs in form.errors.items():
                    for err in errs:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
            return redirect('manage_users')

        user_id = request.POST.get('user_id')
        target_user = get_object_or_404(User, id=user_id)

        if action == 'update_role':
            new_role = request.POST.get('role')
            if new_role in dict(User.ROLE_CHOICES):
                old_role = target_user.role
                target_user.role = new_role
                target_user.save()
                log_audit_trail(
                    request, 'ROLE_CHANGE', 'User', target_user.id,
                    {'old_role': old_role}, {'new_role': new_role},
                    f"Updated role for {target_user.email} to {new_role}"
                )
                messages.success(request, f"Updated role for {target_user.email} to {target_user.get_role_display()}.")

        elif action == 'edit_user':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            role = request.POST.get('role', '').strip()

            if email and User.objects.filter(email=email).exclude(id=target_user.id).exists():
                messages.error(request, f"Email address '{email}' is already in use by another user account.")
            else:
                old_info = {'email': target_user.email, 'role': target_user.role, 'first_name': target_user.first_name, 'last_name': target_user.last_name}
                target_user.first_name = first_name
                target_user.last_name = last_name
                if email:
                    target_user.email = email
                if role in dict(User.ROLE_CHOICES):
                    target_user.role = role
                target_user.save()

                log_audit_trail(
                    request, 'USER_UPDATE', 'User', target_user.id,
                    old_info,
                    {'email': target_user.email, 'role': target_user.role, 'first_name': target_user.first_name, 'last_name': target_user.last_name},
                    f"User details updated for {target_user.email}"
                )
                messages.success(request, f"User details for '{target_user.email}' updated successfully.")

        elif action == 'toggle_active':
            if target_user.id == request.user.id:
                messages.error(request, "You cannot suspend your own active administrator account.")
            else:
                target_user.is_active = not target_user.is_active
                target_user.save()
                status_text = "activated" if target_user.is_active else "suspended"
                log_audit_trail(
                    request, 'USER_UPDATE', 'User', target_user.id,
                    {}, {'is_active': target_user.is_active},
                    f"User account {status_text} for {target_user.email}"
                )
                messages.success(request, f"User account '{target_user.email}' has been {status_text}.")

        elif action == 'delete_user':
            if target_user.id == request.user.id:
                messages.error(request, "You cannot delete your own logged-in administrator account.")
            else:
                user_email = target_user.email
                log_audit_trail(
                    request, 'USER_DELETE', 'User', target_user.id,
                    {'email': user_email, 'role': target_user.role}, {},
                    f"User account deleted for {user_email}"
                )
                target_user.delete()
                messages.success(request, f"User account '{user_email}' has been deleted successfully.")

        return redirect('manage_users')

    users = User.objects.all().order_by('-date_joined')
    context = {
        'users_list': users,
        'role_choices': User.ROLE_CHOICES,
        'register_form': RegisterForm(),
    }
    return render(request, 'users/users_list.html', context)


@login_required
def medication_stock_api(request, medication_id):
    medication = get_object_or_404(Medication, id=medication_id)
    today = timezone.now().date()
    valid_batches = medication.batches.filter(expiry_date__gt=today).order_by('expiry_date')
    
    batches_data = []
    for batch in valid_batches:
        batches_data.append({
            'batch_number': batch.batch_number,
            'quantity': batch.quantity,
            'expiry_date': batch.expiry_date.strftime('%Y-%m-%d'),
            'days_to_expiry': batch.days_to_expiry
        })

    return JsonResponse({
        'id': medication.id,
        'name': medication.name,
        'sku': medication.sku,
        'non_expired_stock': medication.current_stock,
        'batches': batches_data
    })


# FR1 & Dashboard View
@require_permission('view_stock_dashboard')
def dashboard_view(request):
    ensure_master_defaults()
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

    # Section-level stock summary breakdown
    sections = PharmacySection.objects.all().order_by('name')
    sections_summary = []
    for sec in sections:
        sec_meds = sec.medications.all()
        sec_units = sum(m.current_stock for m in sec_meds)
        sec_valuation = sum(m.current_stock * float(m.unit_cost) for m in sec_meds)
        sec_alert_count = sum(1 for m in sec_meds if m.current_stock <= m.reorder_point)
        sections_summary.append({
            'section': sec,
            'skus_count': sec_meds.count(),
            'total_units': sec_units,
            'valuation': sec_valuation,
            'alert_count': sec_alert_count,
        })

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
        'sections_summary': sections_summary,
    }
    return render(request, 'dashboard.html', context)


# 3.2.2.1 Goods Receipt Intake View
@require_permission('record_stock_receipt')
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
        NotificationService.send_bulk_notification(
            recipients=User.objects.all(),
            actor=request.user,
            title="Goods Receipt Intake",
            message=f"Batch {batch.batch_number} ({batch.quantity} {med.unit}) added for {med.name}.",
            target_obj=batch,
            category='stock_receipt'
        )
        messages.success(request, f"Goods Receipt committed! Batch {batch.batch_number} ({batch.quantity} {med.unit}) added for {med.name}.")
        return redirect('medications_list')

    return render(request, 'inventory/receive_batch.html', {'form': form})






# Physical Stock Count Adjustment View
@require_permission('record_stock_adjustment')
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
@require_permission('search_drug_records')
def medications_list_view(request):
    ensure_master_defaults()
    query = request.GET.get('q', '')
    section_id = request.GET.get('section', '')
    page = request.GET.get('page', 1)

    medications_qs = Medication.objects.all().order_by('name')
    if query:
        medications_qs = medications_qs.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    if section_id:
        medications_qs = medications_qs.filter(section_id=section_id)

    paginator = Paginator(medications_qs, 10)
    try:
        medications = paginator.page(page)
    except PageNotAnInteger:
        medications = paginator.page(1)
    except EmptyPage:
        medications = paginator.page(paginator.num_pages)

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


@require_permission('configure_system')
def add_medication_view(request):
    form = MedicationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        med = form.save()
        log_audit_trail(request, 'CONFIG_CHANGE', 'Medication', med.id, {}, {'name': med.name, 'sku': med.sku}, 'New Drug Registered')
        messages.success(request, f"Medication '{med.name}' registered with computed ROP: {med.reorder_point} and EOQ: {med.eoq}.")
    return redirect('medications_list')


# FR3 & FR4: Purchase Orders & Automated Draft PO Generation
@require_permission('approve_purchase_orders')
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


@require_permission('acknowledge_rop')
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
        notes=f"Auto Reorder Trigger: Stock ({med.current_stock}) reached reorder level ({med.reorder_point}). Suggested Qty: {eoq_qty}"
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        medication=med,
        quantity_ordered=eoq_qty,
        eoq_recommended_qty=eoq_qty,
        unit_price=med.unit_cost
    )
    log_audit_trail(request, 'PO_CREATE', 'PurchaseOrder', po.id, {}, {'po_number': po.po_number, 'medication': med.name}, 'Automated Reorder Draft PO Generation')
    NotificationService.send_bulk_notification(
        recipients=User.objects.all(),
        actor=request.user,
        title="Draft PO Created",
        message=f"Draft Purchase Order {po.po_number} created for {med.name} with suggested quantity {eoq_qty}.",
        target_obj=po,
        category='po_created'
    )
    messages.success(request, f"Draft Purchase Order {po.po_number} created for {med.name} with suggested quantity {eoq_qty}.")
    if request.user.can_approve_purchase_orders:
        return redirect('purchase_orders')
    return redirect('medications_list')


@require_permission('approve_purchase_orders')
def approve_po_view(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    po.status = 'APPROVED'
    po.save()
    log_audit_trail(request, 'PO_APPROVE', 'PurchaseOrder', po.id, {'status': 'DRAFT'}, {'status': 'APPROVED'}, 'PO Manager Approval')
    NotificationService.send_bulk_notification(
        recipients=User.objects.all(),
        actor=request.user,
        title="Purchase Order Approved",
        message=f"Purchase Order {po.po_number} has been approved by {request.user.first_name or request.user.email}.",
        target_obj=po,
        category='po_approved'
    )
    messages.success(request, f"Purchase Order {po.po_number} Approved.")
    return redirect('purchase_orders')


# FR6: ABC Classification Console View
@require_permission('review_abc_classification')
def abc_classification_view(request):
    abc_data = calculate_abc_classification()
    context = {
        'abc_data': abc_data,
    }
    return render(request, 'analytics/abc_classification.html', context)


# FR7: Expiry Monitoring & Quarantine View
@require_permission('acknowledge_rop')
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


@require_permission('acknowledge_rop')
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
    NotificationService.send_bulk_notification(
        recipients=User.objects.all(),
        actor=request.user,
        title="Batch Quarantined",
        message=f"Batch {batch.batch_number} for {batch.medication.name} has been quarantined.",
        target_obj=batch,
        category='quarantine_notice'
    )
    messages.warning(request, f"Batch {batch.batch_number} for {batch.medication.name} has been quarantined.")
    return redirect('expiries_monitoring')


# FR2: Immutable Audit Ledger View
@require_permission('view_audit_trail')
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
@require_permission('generate_reports')
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


@require_permission('generate_reports')
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
        writer.writerow(['SKU', 'Medication Name', 'Annual Demand', 'Unit Cost (₦)', 'Annual Consumption Value (₦)', 'Cumulative %', 'ABC Category'])
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


# FR5+: FEFO Dispensing with Cart System and Sales Transactions
@require_permission('dispense_stock')
def fefo_dispense_view(request):
    """Multi-item FEFO dispensing and POS sales management view."""
    ensure_master_defaults()
    today = timezone.now().date()
    
    medications = Medication.objects.all().select_related('section', 'supplier').prefetch_related('batches').order_by('name')
    
    catalog = {}
    for med in medications:
        active_batches = med.batches.filter(quantity__gt=0, expiry_date__gt=today).order_by('expiry_date')
        batches_list = [{
            'id': b.id,
            'batch_number': b.batch_number,
            'quantity': b.quantity,
            'expiry_date': b.expiry_date.strftime('%Y-%m-%d'),
            'days_to_expiry': b.days_to_expiry,
        } for b in active_batches]
        
        catalog[str(med.id)] = {
            'id': med.id,
            'name': med.name,
            'sku': med.sku,
            'unit': med.unit,
            'section': med.section.name if med.section else 'General',
            'supplier': med.supplier.name if med.supplier else 'N/A',
            'unit_cost': float(med.unit_cost),
            'selling_price': float(med.selling_price_per_unit),
            'non_expired_stock': med.non_expired_stock,
            'reorder_point': med.reorder_point,
            'min_level': med.min_level,
            'batches': batches_list,
        }
        
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sales_qs = SalesTransaction.objects.filter(created_at__gte=today_start)
    today_sales_total = today_sales_qs.aggregate(Sum('total_amount_naira'))['total_amount_naira__sum'] or 0.00
    today_tx_count = today_sales_qs.count()
    today_units_total = SalesTransactionItem.objects.filter(sales_transaction__created_at__gte=today_start).aggregate(Sum('quantity_sold'))['quantity_sold__sum'] or 0
    
    recent_sales = SalesTransaction.objects.all().prefetch_related('items__medication', 'pharmacist').order_by('-created_at')[:15]
    
    context = {
        'medications': medications,
        'catalog_json': json.dumps(catalog),
        'today_sales_total': float(today_sales_total),
        'today_tx_count': today_tx_count,
        'today_units_total': today_units_total,
        'recent_sales': recent_sales,
        'payment_methods': SalesTransaction.PAYMENT_METHODS,
        'selected_med_id': request.GET.get('medication', '')
    }
    return render(request, 'inventory/fefo_dispense.html', context)


@require_permission('dispense_stock')
def cart_add_item(request):
    """AJAX endpoint to add medication to cart."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        medication_id = data.get('medication_id')
        quantity = int(data.get('quantity', 1))

        if quantity <= 0:
            return JsonResponse({'error': 'Quantity must be greater than zero'}, status=400)

        medication = get_object_or_404(Medication, id=medication_id)

        # Validate available stock (non-expired)
        today = timezone.now().date()
        available_stock = medication.batches.filter(quantity__gt=0, expiry_date__gt=today).aggregate(Sum('quantity'))['quantity__sum'] or 0

        # Initialize cart in session if not exists
        if 'cart' not in request.session:
            request.session['cart'] = {}

        cart = request.session['cart']
        med_id_str = str(medication_id)
        current_in_cart = cart.get(med_id_str, {}).get('quantity', 0)
        new_total_qty = current_in_cart + quantity

        if new_total_qty > available_stock:
            return JsonResponse({
                'error': f'Cannot add {quantity} units. Only {available_stock} non-expired units available in inventory (currently in cart: {current_in_cart}).',
                'available': available_stock
            }, status=400)

        if med_id_str in cart:
            cart[med_id_str]['quantity'] = new_total_qty
        else:
            cart[med_id_str] = {
                'medication_id': medication.id,
                'name': medication.name,
                'sku': medication.sku,
                'unit': medication.unit,
                'quantity': quantity,
                'unit_price': float(medication.selling_price_per_unit)
            }

        request.session['cart'] = cart
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'message': f'Added {quantity} {medication.unit} of {medication.name} to cart',
            'cart_count': sum(item['quantity'] for item in cart.values()),
            'unique_items': len(cart)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_permission('dispense_stock')
def cart_update_item(request):
    """AJAX endpoint to update cart item quantity."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        medication_id = data.get('medication_id')
        quantity = int(data.get('quantity', 0))

        if 'cart' not in request.session:
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        cart = request.session['cart']
        med_id_str = str(medication_id)

        if med_id_str not in cart:
            return JsonResponse({'error': 'Item not in cart'}, status=404)

        if quantity <= 0:
            del cart[med_id_str]
            request.session['cart'] = cart
            request.session.modified = True
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'cart_count': sum(item['quantity'] for item in cart.values()),
                'unique_items': len(cart)
            })

        medication = get_object_or_404(Medication, id=medication_id)

        # Validate available stock
        today = timezone.now().date()
        available_stock = medication.batches.filter(quantity__gt=0, expiry_date__gt=today).aggregate(Sum('quantity'))['quantity__sum'] or 0

        if quantity > available_stock:
            return JsonResponse({
                'error': f'Cannot set quantity to {quantity}. Only {available_stock} non-expired units available.',
                'available': available_stock
            }, status=400)

        cart[med_id_str]['quantity'] = quantity
        request.session['cart'] = cart
        request.session.modified = True

        return JsonResponse({
            'success': True,
            'message': 'Cart updated successfully',
            'cart_count': sum(item['quantity'] for item in cart.values()),
            'unique_items': len(cart)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_permission('dispense_stock')
def cart_remove_item(request):
    """AJAX endpoint to remove item from cart."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    try:
        data = json.loads(request.body)
        medication_id = data.get('medication_id')

        if 'cart' not in request.session:
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        cart = request.session['cart']
        med_id_str = str(medication_id)

        if med_id_str in cart:
            med_name = cart[med_id_str]['name']
            del cart[med_id_str]
            request.session['cart'] = cart
            request.session.modified = True

            return JsonResponse({
                'success': True,
                'message': f'Removed {med_name} from cart',
                'cart_count': sum(item['quantity'] for item in cart.values()),
                'unique_items': len(cart)
            })

        return JsonResponse({'error': 'Item not found in cart'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_permission('dispense_stock')
def cart_get_contents(request):
    """AJAX endpoint to get current cart contents and totals with live stock counts."""
    if 'cart' not in request.session:
        return JsonResponse({
            'items': [],
            'total_units': 0,
            'total_naira': 0.00,
            'item_count': 0
        })

    cart = request.session['cart']
    items = []
    total_naira = 0
    total_units = 0
    today = timezone.now().date()

    for med_id_str, item in cart.items():
        qty = item['quantity']
        price = item['unit_price']
        subtotal = qty * price
        total_naira += subtotal
        total_units += qty

        # Get fresh available stock
        med = Medication.objects.filter(id=item['medication_id']).first()
        available_stock = med.batches.filter(quantity__gt=0, expiry_date__gt=today).aggregate(Sum('quantity'))['quantity__sum'] or 0 if med else 0

        items.append({
            'medication_id': item['medication_id'],
            'name': item['name'],
            'sku': item['sku'],
            'unit': item['unit'],
            'quantity': qty,
            'unit_price': price,
            'subtotal': subtotal,
            'available_stock': available_stock
        })

    return JsonResponse({
        'items': items,
        'total_units': total_units,
        'total_naira': float(total_naira),
        'item_count': len(items)
    })


@require_permission('dispense_stock')
def cart_clear(request):
    """AJAX endpoint to clear entire cart."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    request.session['cart'] = {}
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'message': 'Cart cleared',
        'cart_count': 0,
        'unique_items': 0
    })


@require_permission('dispense_stock')
def checkout_and_dispense(request):
    """Finalize sale: create SalesTransaction, perform FEFO dispensing, update stock, log immutable audit trail."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    if 'cart' not in request.session or not request.session['cart']:
        return JsonResponse({'error': 'Cart is currently empty. Please add medications before checkout.'}, status=400)

    try:
        data = json.loads(request.body)
        patient_info = data.get('patient_info', '').strip()
        payment_method = data.get('payment_method', 'CASH').strip()
        if payment_method == 'POS':
            payment_method = 'POS_CARD'
        notes = data.get('notes', '').strip()

        cart = request.session['cart']
        today = timezone.now().date()

        with transaction.atomic():
            # Create sales transaction
            sales_tx = SalesTransaction.objects.create(
                pharmacist=request.user,
                patient_info=patient_info,
                payment_method=payment_method,
                notes=notes
            )

            total_amount = 0
            dispensed_summary = []

            for med_id_str, cart_item in cart.items():
                medication_id = cart_item['medication_id']
                quantity_to_dispense = int(cart_item['quantity'])
                unit_price = float(cart_item['unit_price'])

                medication = get_object_or_404(Medication, id=medication_id)

                # FEFO: Get active non-expired batches ordered by earliest expiry date first
                active_batches = medication.batches.filter(quantity__gt=0, expiry_date__gt=today).order_by('expiry_date')

                total_available = sum(b.quantity for b in active_batches)
                if quantity_to_dispense > total_available:
                    raise ValueError(f"Insufficient stock for {medication.name}. Available non-expired: {total_available}, Requested: {quantity_to_dispense}")

                # Perform FEFO deduction
                remaining_needed = quantity_to_dispense
                batch_details = []
                before_stock = medication.current_stock

                for batch in active_batches:
                    if remaining_needed <= 0:
                        break

                    deduct = min(batch.quantity, remaining_needed)
                    batch.quantity -= deduct
                    batch.save()
                    remaining_needed -= deduct

                    batch_details.append({
                        'batch_number': batch.batch_number,
                        'expiry_date': str(batch.expiry_date),
                        'deducted_qty': deduct
                    })

                after_stock = medication.current_stock

                # Create sales transaction item
                subtotal = quantity_to_dispense * unit_price
                total_amount += subtotal

                SalesTransactionItem.objects.create(
                    sales_transaction=sales_tx,
                    medication=medication,
                    quantity_sold=quantity_to_dispense,
                    unit_price_naira=unit_price,
                    subtotal_naira=subtotal
                )

                dispensed_summary.append({
                    'medication_id': medication.id,
                    'name': medication.name,
                    'sku': medication.sku,
                    'unit': medication.unit,
                    'quantity': quantity_to_dispense,
                    'unit_price': unit_price,
                    'subtotal': subtotal,
                    'batches': batch_details,
                    'before_stock': before_stock,
                    'remaining_stock': after_stock
                })

                # Log immutable StockAuditLedger entry
                batch_str_list = [f"Batch {b['batch_number']} (Exp: {b['expiry_date']}): -{b['deducted_qty']}" for b in batch_details]
                log_audit_trail(
                    request,
                    'DISPENSE_FEFO',
                    'Medication',
                    medication.id,
                    {'stock': before_stock},
                    {
                        'stock': after_stock,
                        'dispensed_qty': quantity_to_dispense,
                        'batches': batch_str_list,
                        'unit_price_naira': float(unit_price),
                        'subtotal_naira': float(subtotal),
                        'transaction_ref': sales_tx.transaction_ref
                    },
                    f"POS Sale #{sales_tx.transaction_ref}: Dispensed {quantity_to_dispense} {medication.unit} @ ₦{unit_price:,.2f} ({sales_tx.get_payment_method_display()})"
                )

                # Real-time alert notifications for low stock & ROP breach
                if after_stock == 0:
                    NotificationService.send_bulk_notification(
                        recipients=User.objects.all(),
                        actor=request.user,
                        title="OUT OF STOCK ALERT",
                        message=f"Critical: {medication.name} is now completely out of stock!",
                        target_obj=medication,
                        category='out_of_stock'
                    )
                elif after_stock <= medication.reorder_point:
                    NotificationService.send_bulk_notification(
                        recipients=User.objects.all(),
                        actor=request.user,
                        title="ROP BREACH ALERT",
                        message=f"Warning: {medication.name} stock ({after_stock}) has reached or dropped below ROP ({medication.reorder_point}).",
                        target_obj=medication,
                        category='rop_alert'
                    )

            # Update transaction total
            sales_tx.total_amount_naira = total_amount
            sales_tx.save()

            # Clear cart session
            request.session['cart'] = {}
            request.session.modified = True

            return JsonResponse({
                'success': True,
                'transaction_ref': sales_tx.transaction_ref,
                'total_amount_naira': float(total_amount),
                'payment_method': sales_tx.get_payment_method_display(),
                'patient_info': sales_tx.patient_info,
                'notes': sales_tx.notes,
                'pharmacist': request.user.first_name or request.user.email,
                'created_at': sales_tx.created_at.strftime('%b %d, %Y %I:%M %p'),
                'total_units': sum(s['quantity'] for s in dispensed_summary),
                'items_count': len(dispensed_summary),
                'dispensed_items': dispensed_summary,
                'message': f'Dispense and Sale completed successfully! Ref: {sales_tx.transaction_ref}'
            })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Checkout error: {str(e)}'}, status=500)


@login_required
def sales_receipt_view(request, transaction_ref):
    """View / print / download a sales receipt."""
    sales_tx = get_object_or_404(SalesTransaction.objects.prefetch_related('items__medication'), transaction_ref=transaction_ref)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        items_data = [{
            'medication_name': item.medication.name if item.medication else 'Unknown Item',
            'sku': item.medication.sku if item.medication else 'N/A',
            'unit': item.medication.unit if item.medication else 'unit',
            'quantity': item.quantity_sold,
            'unit_price': float(item.unit_price_naira),
            'subtotal': float(item.subtotal_naira)
        } for item in sales_tx.items.all()]
        
        return JsonResponse({
            'transaction_ref': sales_tx.transaction_ref,
            'created_at': sales_tx.created_at.strftime('%b %d, %Y %I:%M %p'),
            'pharmacist': sales_tx.pharmacist.email if sales_tx.pharmacist else 'System',
            'patient_info': sales_tx.patient_info,
            'payment_method': sales_tx.get_payment_method_display(),
            'notes': sales_tx.notes,
            'total_amount_naira': float(sales_tx.total_amount_naira),
            'items': items_data
        })
        
    return render(request, 'inventory/sales_receipt.html', {'transaction': sales_tx})



