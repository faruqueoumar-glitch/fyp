from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import PharmacySection, Medication, MedicationBatch, Supplier, PurchaseOrder

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs',
            'placeholder': 'Enter strong password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs',
                'placeholder': 'name@hospital.org'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs font-bold'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('password')
        cpwd = cleaned_data.get('confirm_password')

        if pwd and cpwd and pwd != cpwd:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs',
            'placeholder': 'pharmacist@hospital.org'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border-2 border-black bg-white focus:outline-none font-mono text-xs',
            'placeholder': '••••••••••••'
        })
    )


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'contact_person': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'phone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'address': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'rows': 2}),
        }


class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = [
            'name', 'sku', 'section', 'supplier', 'unit', 'unit_cost',
            'annual_demand', 'ordering_cost', 'holding_cost',
            'daily_consumption', 'lead_time_days', 'safety_stock', 'max_level'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'sku': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'section': forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'supplier': forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'unit': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'step': '0.01'}),
            'annual_demand': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'ordering_cost': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'step': '0.01'}),
            'holding_cost': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'step': '0.01'}),
            'daily_consumption': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'lead_time_days': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'safety_stock': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'max_level': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
        }


class GoodsReceiptForm(forms.ModelForm):
    """3.2.2.1 Capturing drug identity, supplier, batch number, manufacture date, expiry date, and quantity received."""
    class Meta:
        model = MedicationBatch
        fields = ['medication', 'supplier', 'batch_number', 'initial_quantity', 'manufacture_date', 'expiry_date']
        widgets = {
            'medication': forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs font-bold'}),
            'supplier': forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'}),
            'batch_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'placeholder': 'e.g. BAT-2026-X9'}),
            'initial_quantity': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'placeholder': 'e.g. 500'}),
            'manufacture_date': forms.DateInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        mfg = cleaned.get('manufacture_date')
        exp = cleaned.get('expiry_date')
        if mfg and exp and exp <= mfg:
            self.add_error('expiry_date', 'Expiry date must be after manufacture date.')
        return cleaned


class FEFODispenseForm(forms.Form):
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.all(),
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs font-bold'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'placeholder': 'e.g. 30'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'placeholder': 'Prescription ID / Dispense rationale'})
    )


class StockAdjustmentForm(forms.Form):
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.all(),
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs font-bold'})
    )
    actual_physical_count = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs', 'rows': 2, 'placeholder': 'Discrepancy audit justification'})
    )


class PurchaseOrderForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs font-bold'})
    )
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.all(),
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs font-bold'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border-2 border-black bg-white font-mono text-xs'})
    )
