import django.db.models.deletion
from django.db import migrations, models


TENANT_MODELS = (
    'CustomUser',
    'Supplier',
    'PharmacySection',
    'Medication',
    'MedicationBatch',
    'PurchaseOrder',
    'PurchaseOrderItem',
    'StockAuditLedger',
    'SalesTransaction',
    'SalesTransactionItem',
)


def assign_existing_records_to_legacy_pharmacy(apps, schema_editor):
    database = schema_editor.connection.alias
    Pharmacy = apps.get_model('app', 'Pharmacy')
    pharmacy, _ = Pharmacy.objects.using(database).get_or_create(
        shop_name='Legacy Pharmacy',
        email='legacy-pharmacy@invalid.local',
        defaults={'address': 'Imported from the pre-tenant installation'},
    )
    for model_name in TENANT_MODELS:
        model = apps.get_model('app', model_name)
        model.objects.using(database).all().update(pharmacy_id=pharmacy.pk)


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_salestransaction_payment_method_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pharmacy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shop_name', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=254)),
                ('address', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        *[
            migrations.AddField(
                model_name=model_name.lower(),
                name='pharmacy',
                field=models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='%(class)s_records',
                    to='app.pharmacy',
                ),
            )
            for model_name in TENANT_MODELS
        ],
        migrations.AlterModelOptions(
            name='customuser',
            options={},
        ),
        migrations.AlterField(
            model_name='supplier',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='pharmacysection',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='pharmacysection',
            name='code',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='medication',
            name='sku',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='purchaseorder',
            name='po_number',
            field=models.CharField(editable=False, max_length=50),
        ),
        migrations.AlterField(
            model_name='stockauditledger',
            name='transaction_id',
            field=models.CharField(editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name='salestransaction',
            name='transaction_ref',
            field=models.CharField(editable=False, max_length=50),
        ),
        migrations.RunPython(
            assign_existing_records_to_legacy_pharmacy,
            migrations.RunPython.noop,
        ),
        *[
            migrations.AlterField(
                model_name=model_name.lower(),
                name='pharmacy',
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='%(class)s_records',
                    to='app.pharmacy',
                ),
            )
            for model_name in TENANT_MODELS
        ],
        migrations.AddConstraint(
            model_name='supplier',
            constraint=models.UniqueConstraint(fields=('pharmacy', 'name'), name='unique_supplier_name_pharm'),
        ),
        migrations.AddConstraint(
            model_name='pharmacysection',
            constraint=models.UniqueConstraint(fields=('pharmacy', 'name'), name='unique_section_name_pharm'),
        ),
        migrations.AddConstraint(
            model_name='pharmacysection',
            constraint=models.UniqueConstraint(fields=('pharmacy', 'code'), name='unique_section_code_pharm'),
        ),
        migrations.AddConstraint(
            model_name='medication',
            constraint=models.UniqueConstraint(fields=('pharmacy', 'sku'), name='unique_medication_sku_pharm'),
        ),
        migrations.AddConstraint(
            model_name='purchaseorder',
            constraint=models.UniqueConstraint(fields=('pharmacy', 'po_number'), name='unique_po_number_pharm'),
        ),
        migrations.AddConstraint(
            model_name='stockauditledger',
            constraint=models.UniqueConstraint(fields=('pharmacy', 'transaction_id'), name='unique_audit_id_pharm'),
        ),
        migrations.AddConstraint(
            model_name='salestransaction',
            constraint=models.UniqueConstraint(fields=('pharmacy', 'transaction_ref'), name='unique_sale_ref_pharm'),
        ),
    ]
