from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from app.tenancy import pharmacy_context
from .models import (
    CustomUser,
    Pharmacy,
    Supplier,
    PharmacySection,
    Medication,
    MedicationBatch,
    PurchaseOrder,
    PurchaseOrderItem,
    StockAuditLedger,
    SalesTransaction,
    SalesTransactionItem,

)

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    # list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Pharmacy', {'fields': ('pharmacy',)}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name', 'pharmacy'),
        }),
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    def save_model(self, request, obj, form, change):
        if request.user.is_superuser and not change and obj.pharmacy_id:
            with pharmacy_context(obj.pharmacy_id):
                super().save_model(request, obj, form, change)
            return
        super().save_model(request, obj, form, change)


admin.site.register(Pharmacy)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Supplier)
admin.site.register(PharmacySection)
admin.site.register(Medication)
admin.site.register(MedicationBatch)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(StockAuditLedger)
admin.site.register(SalesTransaction)
admin.site.register(SalesTransactionItem)