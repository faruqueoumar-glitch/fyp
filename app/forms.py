from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import PharmacySection, Medication, MedicationBatch, Supplier, PurchaseOrder

User = get_user_model()

INPUT_CLASS = 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition-all duration-200'
SELECT_CLASS = 'w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition-all duration-200'

UNIT_OF_MEASURE_CHOICES = [
    ('Tablets', 'Tablets (tab)'),
    ('Capsules', 'Capsules (cap)'),
    ('Vials', 'Vials (vial)'),
    ('Ampoules', 'Ampoules (amp)'),
    ('Bottles', 'Bottles (bctl)'),
    ('Blisters', 'Blisters (blist)'),
    ('Syringes', 'Syringes (syr)'),
    ('Sachets', 'Sachets (sach)'),
    ('Boxes', 'Boxes (box)'),
    ('Tubes', 'Tubes (tb)'),
    ('Packs', 'Packs (pack)'),
    ('Drops', 'Drops (drp)'),
    ('Inhalers', 'Inhalers (inh)'),
    ('Suppositories', 'Suppositories (supp)'),
    ('Ointments', 'Ointment / Cream (g)'),
    ('Suspension', 'Suspension (mL)'),
    ('Solution', 'Solution (mL)'),
    ('IV Bags', 'IV Bags (bag)'),
]


class RegisterForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        initial='PHARMACIST',
        required=False,
        widget=forms.Select(attrs={'class': SELECT_CLASS})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Enter password',
            'id': 'registerPassword'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Confirm password',
            'id': 'registerConfirmPassword'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'name@hospital.org'
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
            'class': INPUT_CLASS,
            'placeholder': 'pharmacist@hospital.org'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': '••••••••••••',
            'id': 'loginPassword'
        })
    )


class PharmacySectionForm(forms.ModelForm):
    class Meta:
        model = PharmacySection
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Outpatient Pharmacy'}),
            'code': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. SEC-OUTP'}),
            'description': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2, 'placeholder': 'Section notes and location details'}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Fidson Healthcare Plc'}),
            'contact_person': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Dr. Alabi Williams'}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'info@fidson.com'}),
            'phone': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': '+234-803-000-1122'}),
            'address': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2, 'placeholder': 'Physical company address'}),
        }


class MedicationForm(forms.ModelForm):
    unit = forms.ChoiceField(
        choices=UNIT_OF_MEASURE_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS})
    )

    class Meta:
        model = Medication
        fields = [
            'name', 'sku', 'section', 'supplier', 'unit', 'unit_cost', 'selling_price_per_unit',
            'annual_demand', 'ordering_cost', 'holding_cost',
            'daily_consumption', 'lead_time_days', 'safety_stock', 'max_level'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Amoxicillin 500mg'}),
            'sku': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. SKU-AMX-500'}),
            'section': forms.Select(attrs={'class': SELECT_CLASS}),
            'supplier': forms.Select(attrs={'class': SELECT_CLASS}),
            'unit_cost': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'placeholder': '100.00', 'min': '10'}),
            'selling_price_per_unit': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'placeholder': '200.00', 'min': '50'}),
            'annual_demand': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '3600'}),
            'ordering_cost': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'placeholder': '500.00'}),
            'holding_cost': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'placeholder': '20.00'}),
            'daily_consumption': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '10'}),
            'lead_time_days': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '7'}),
            'safety_stock': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '50'}),
            'max_level': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': '500'}),
        }
        help_texts = {
            'selling_price_per_unit': 'Price in Nigerian Naira (₦). Standard prices: ₦50, ₦100, ₦200, ₦500, etc.'
        }


class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = MedicationBatch
        fields = ['medication', 'supplier', 'batch_number', 'initial_quantity', 'manufacture_date', 'expiry_date']
        widgets = {
            'medication': forms.Select(attrs={'class': SELECT_CLASS}),
            'supplier': forms.Select(attrs={'class': SELECT_CLASS}),
            'batch_number': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. BAT-2026-X9'}),
            'initial_quantity': forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. 500'}),
            'manufacture_date': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
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
        widget=forms.Select(attrs={'class': SELECT_CLASS})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. 30'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Prescription ID / Dispense rationale'})
    )


class StockAdjustmentForm(forms.Form):
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.all(),
        widget=forms.Select(attrs={'class': SELECT_CLASS})
    )
    actual_physical_count = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASS})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2, 'placeholder': 'Discrepancy audit justification'})
    )


class PurchaseOrderForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        widget=forms.Select(attrs={'class': SELECT_CLASS})
    )
    medication = forms.ModelChoiceField(
        queryset=Medication.objects.all(),
        widget=forms.Select(attrs={'class': SELECT_CLASS})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASS})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS})
    )
