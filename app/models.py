import hashlib
import math
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils import timezone

ROLE_PERMISSIONS = {
    'ADMIN': {
        'manage_users',
        'configure_system',
        'manage_suppliers',
        'view_stock_dashboard',
        'search_drug_records',
        'view_audit_trail',
    },
    'PHARMACIST': {
        'view_stock_dashboard',
        'record_stock_receipt',
        'dispense_stock',
        'acknowledge_rop',
        'record_stock_adjustment',
        'search_drug_records',
    },
    'MANAGER': {
        'view_stock_dashboard',
        'acknowledge_rop',
        'search_drug_records',
        'generate_reports',
        'approve_purchase_orders',
        'review_abc_classification',
        'view_audit_trail',
    },
}


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'System Administrator'),
        ('PHARMACIST', 'Pharmacist'),
        ('MANAGER', 'Inventory Manager'),
    )

    username = None
    email = models.EmailField('email address', unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PHARMACIST')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} [{self.get_role_display()}]"

    def has_permission(self, permission_name):
        """Explicit permission verification based on defined RBAC matrix."""
        if not self.is_authenticated:
            return False
        if self.is_superuser:
            return True
        allowed_perms = ROLE_PERMISSIONS.get(self.role, set())
        return permission_name in allowed_perms

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            role_to_group = {
                'ADMIN': 'Admin',
                'PHARMACIST': 'Pharmacist',
                'MANAGER': 'Manager',
            }
            group_name = role_to_group.get(self.role)
            if group_name:
                group, _ = Group.objects.get_or_create(name=group_name)
                for other_name in role_to_group.values():
                    if other_name != group_name:
                        other_g = Group.objects.filter(name=other_name).first()
                        if other_g:
                            self.groups.remove(other_g)
                self.groups.add(group)
        except Exception:
            pass

    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.is_superuser

    @property
    def is_pharmacist(self):
        return self.role == 'PHARMACIST' or self.is_superuser

    @property
    def is_manager(self):
        return self.role == 'MANAGER' or self.is_superuser

    # Explicit granular permission properties
    @property
    def can_manage_users(self):
        return self.has_permission('manage_users')

    @property
    def can_configure_system(self):
        return self.has_permission('configure_system')

    @property
    def can_manage_suppliers(self):
        return self.has_permission('manage_suppliers')

    @property
    def can_view_stock_dashboard(self):
        return self.has_permission('view_stock_dashboard')

    @property
    def can_search_drug_records(self):
        return self.has_permission('search_drug_records')

    @property
    def can_view_audit_trail(self):
        return self.has_permission('view_audit_trail')

    @property
    def can_record_stock_receipt(self):
        return self.has_permission('record_stock_receipt')

    @property
    def can_dispense_stock(self):
        return self.has_permission('dispense_stock')

    @property
    def can_acknowledge_rop(self):
        return self.has_permission('acknowledge_rop')

    @property
    def can_record_stock_adjustment(self):
        return self.has_permission('record_stock_adjustment')

    @property
    def can_generate_reports(self):
        return self.has_permission('generate_reports')

    @property
    def can_approve_purchase_orders(self):
        return self.has_permission('approve_purchase_orders')

    @property
    def can_review_abc_classification(self):
        return self.has_permission('review_abc_classification')


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PharmacySection(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Medication(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    section = models.ForeignKey(PharmacySection, on_delete=models.CASCADE, related_name='medications')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='medications')
    unit = models.CharField(max_length=50, default='Tablets')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=100.00, help_text="Unit purchase price in Nigerian Naira")
    selling_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=200.00, help_text="Selling price per unit in Nigerian Naira")

    # FR3: Economic Order Quantity (EOQ) Parameters
    annual_demand = models.PositiveIntegerField(default=3600, help_text="Configured annual demand units")
    ordering_cost = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, help_text="Ordering cost S per PO in Nigerian Naira")
    holding_cost = models.DecimalField(max_digits=10, decimal_places=2, default=20.00, help_text="Annual holding cost H per unit in Nigerian Naira")

    # FR4: Min-Max & ROP Parameters
    daily_consumption = models.PositiveIntegerField(default=10, help_text="Average daily usage units")
    lead_time_days = models.PositiveIntegerField(default=7, help_text="Supplier lead time in days")
    safety_stock = models.PositiveIntegerField(default=50, help_text="Safety stock (Minimum Level)")
    max_level = models.PositiveIntegerField(default=500, help_text="Maximum capacity limit")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.sku}]"

    @property
    def reorder_point(self):
        """ROP = (Daily Consumption * Lead Time) + Safety Stock"""
        return (self.daily_consumption * self.lead_time_days) + self.safety_stock

    @property
    def min_level(self):
        return self.safety_stock

    @property
    def eoq(self):
        """FR3: EOQ Formula = sqrt((2 * Demand * OrderCost) / HoldingCost)"""
        try:
            d = float(self.annual_demand)
            s = float(self.ordering_cost)
            h = float(self.holding_cost)
            if h > 0:
                result = math.sqrt((2 * d * s) / h)
                return round(result)
        except Exception:
            pass
        return 100

    @property
    def current_stock(self):
        total = self.batches.filter(quantity__gt=0).aggregate(models.Sum('quantity'))['quantity__sum']
        return total or 0

    @property
    def non_expired_stock(self):
        today = timezone.now().date()
        total = self.batches.filter(quantity__gt=0, expiry_date__gt=today).aggregate(models.Sum('quantity'))['quantity__sum']
        return total or 0

    @property
    def annual_consumption_value(self):
        """FR6: Annual Consumption Value = Annual Demand * Unit Cost"""
        return float(self.annual_demand) * float(self.unit_cost)

    @property
    def stock_status(self):
        """FR1 Status Indicators"""
        stock = self.current_stock
        rop = self.reorder_point
        min_lvl = self.min_level

        if stock == 0:
            return 'OUT_OF_STOCK'
        elif stock < min_lvl:
            return 'BELOW_MINIMUM'
        elif stock <= rop:
            return 'AT_REORDER_POINT'
        elif stock > self.max_level:
            return 'OVERSTOCKED'
        return 'ADEQUATE'


class MedicationBatch(models.Model):
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='batches')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    batch_number = models.CharField(max_length=100)
    initial_quantity = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    received_date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['expiry_date']

    def __str__(self):
        return f"{self.medication.name} - Batch {self.batch_number} (Exp: {self.expiry_date})"

    @property
    def is_expired(self):
        return self.expiry_date <= timezone.now().date()

    @property
    def days_to_expiry(self):
        delta = self.expiry_date - timezone.now().date()
        return delta.days

    @property
    def expiry_status(self):
        days = self.days_to_expiry
        if days <= 0:
            return 'EXPIRED'
        elif days <= 30:
            return 'CRITICAL_30_DAYS'
        elif days <= 90:
            return 'WARNING_90_DAYS'
        return 'HEALTHY'


class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('RECEIVED', 'Received / Closed'),
        ('CANCELLED', 'Cancelled'),
    )

    po_number = models.CharField(max_length=50, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = f"PO-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} [{self.get_status_display()}]"

    @property
    def total_cost(self):
        total = sum(item.total_price for item in self.items.all())
        return total


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()
    eoq_recommended_qty = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.purchase_order.po_number}: {self.medication.name} x {self.quantity_ordered}"

    @property
    def total_price(self):
        return float(self.quantity_ordered) * float(self.unit_price)


class StockAuditLedger(models.Model):
    """FR2: Immutable Audit Trail recording every stock transaction, user login, and data modification."""
    ACTION_TYPES = (
        ('STOCK_RECEIPT', 'Stock Goods Receipt'),
        ('DISPENSE_FEFO', 'Dispensed (FEFO)'),
        ('STOCK_ADJUSTMENT', 'Physical Count Adjustment'),
        ('PO_CREATE', 'Purchase Order Drafted'),
        ('PO_APPROVE', 'Purchase Order Approved'),
        ('USER_LOGIN', 'User Session Login'),
        ('CONFIG_CHANGE', 'System Configuration Change'),
        ('QUARANTINE', 'Expired Batch Isolation'),
    )

    transaction_id = models.CharField(max_length=64, unique=True, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_identity = models.CharField(max_length=150, default='system')
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    affected_entity = models.CharField(max_length=100, default='Medication')
    entity_pk = models.CharField(max_length=100, default='N/A')
    
    before_data = models.TextField(blank=True, default='{}')
    after_data = models.TextField(blank=True, default='{}')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reason = models.TextField(blank=True)

    previous_hash = models.CharField(max_length=64, default='0' * 64)
    current_hash = models.CharField(max_length=64, editable=False)

    class Meta:
        ordering = ['-timestamp']

    def delete(self, *args, **kwargs):
        """FR2: Enforce strict immutability. No audit record shall be modifiable or deletable by any role."""
        raise PermissionDenied("FR2 Violation: Audit trail records are strictly immutable and cannot be deleted.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionDenied("FR2 Violation: Existing audit trail records cannot be modified.")

        if not self.transaction_id:
            self.transaction_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"

        last_entry = StockAuditLedger.objects.order_by('-timestamp', '-id').first()
        if last_entry:
            self.previous_hash = last_entry.current_hash
        else:
            self.previous_hash = 'GENESIS_' + '0' * 56

        payload = f"{self.transaction_id}:{self.user_identity}:{self.action_type}:{self.affected_entity}:{self.entity_pk}:{self.before_data}:{self.after_data}:{self.previous_hash}"
        self.current_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        super().save(*args, **kwargs)

    def verify_integrity(self):
        payload = f"{self.transaction_id}:{self.user_identity}:{self.action_type}:{self.affected_entity}:{self.entity_pk}:{self.before_data}:{self.after_data}:{self.previous_hash}"
        computed = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        return computed == self.current_hash


class SalesTransaction(models.Model):
    """Sales transaction record for medications dispensed and sold."""
    PAYMENT_METHODS = (
        ('CASH', 'Cash (₦)'),
        ('POS_CARD', 'POS / Debit Card (₦)'),
        ('TRANSFER', 'Bank Transfer (₦)'),
        ('INSURANCE', 'Health Insurance / HMO'),
    )

    transaction_ref = models.CharField(max_length=50, unique=True, editable=False)
    pharmacist = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount_naira = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    
    patient_info = models.CharField(max_length=255, blank=True, help_text="Patient name or prescription reference")
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.transaction_ref:
            self.transaction_ref = f"SALE-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_ref} - ₦{self.total_amount_naira:,.2f}"

    @property
    def total_units_sold(self):
        return self.items.aggregate(models.Sum('quantity_sold'))['quantity_sold__sum'] or 0

    @property
    def item_count(self):
        return self.items.count()


class SalesTransactionItem(models.Model):
    """Individual medication items in a sales transaction."""
    sales_transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.SET_NULL, null=True)
    quantity_sold = models.PositiveIntegerField()
    unit_price_naira = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal_naira = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-sales_transaction__created_at', 'medication__name']

    def save(self, *args, **kwargs):
        self.subtotal_naira = self.quantity_sold * self.unit_price_naira
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medication.name} x{self.quantity_sold} @ ₦{self.unit_price_naira}"
