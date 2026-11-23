from django.http import JsonResponse
from django.views import View
import json
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.core.exceptions import PermissionDenied
from .models import (
    CustomUser, Medication, MedicationBatch, SalesTransaction,
    SalesTransactionItem, StockAuditLedger, Pharmacy
)
from .tenancy import pharmacy_context


def json_body_decode(body):
    try:
        if isinstance(body, bytes):
            return json.loads(body.decode('utf-8'))
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


class SyncPushView(View):
    """POST /api/sync/push/"""

    def post(self, request, *args, **kwargs):
        try:
            payload = json_body_decode(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        device_id = payload.get("device_id", "")
        tables = payload.get("tables", {})
        last_sync_ts = payload.get("last_sync_timestamp", "")

        if not device_id:
            return JsonResponse({"error": "device_id required"}, status=400)

        pharmacy_id = None
        with pharmacy_context():
            pharmacy_id = pharmacy_context.get_current_pharmacy_id()

        if not pharmacy_id:
            return JsonResponse({"error": "No pharmacy context"}, status=400)

        audit_entries = []

        for table_name, records in tables.items():
            if table_name == "medication":
                for rec in records:
                    self._sync_medication(rec, pharmacy_id, device_id, audit_entries)
            elif table_name == "medicationbatch":
                for rec in records:
                    self._sync_medication_batch(rec, pharmacy_id, device_id, audit_entries)
            elif table_name == "salestransaction":
                for rec in records:
                    self._sync_sales_transaction(rec, pharmacy_id, device_id, audit_entries)
            elif table_name == "salesttransactionitem":
                for rec in records:
                    self._sync_sales_transaction_item(rec, pharmacy_id, device_id, audit_entries)
            elif table_name == "stockauditedger":
                for rec in records:
                    self._process_audit_record(rec, pharmacy_id, device_id, audit_entries)

        return JsonResponse({
            "status": "ok",
            "audit_entries_created": len(audit_entries),
            "device_id": device_id,
            "pharmacy_id": pharmacy_id,
            "server_timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def _sync_medication(self, rec, pharmacy_id, device_id, audit_entries):
        from .models import Medication
        uuid = rec.get("uuid")
        if not uuid:
            return
        defaults = {
            "name": rec.get("name"), "sku": rec.get("sku"),
            "section_id": rec.get("section_id"), "supplier_id": rec.get("supplier_id"),
            "unit": rec.get("unit", "Tablets"), "drug_schedule": rec.get("drug_schedule", "OTC"),
            "unit_cost": rec.get("unit_cost", 100.00), "selling_price_per_unit": rec.get("selling_price_per_unit", 200.00),
            "annual_demand": rec.get("annual_demand", 3600), "ordering_cost": rec.get("ordering_cost", 500.00),
            "holding_cost": rec.get("holding_cost", 20.00), "daily_consumption": rec.get("daily_consumption", 10),
            "lead_time_days": rec.get("lead_time_days", 7), "safety_stock": rec.get("safety_stock", 50),
            "max_level": rec.get("max_level", 500), "updated_at": rec.get("updated_at", datetime.now()),
            "last_sync_device": device_id,
        }
        audit_entries.append({
            "action_type": "SYNC_MEDICATION", "affected_entity": "Medication", "entity_pk": uuid,
            "user_identity": device_id,
            "reason": f"Medication synced from device {device_id}",
        })
        Medication.objects.update_or_create(uuid=uuid, defaults=defaults)

    def _sync_medication_batch(self, rec, pharmacy_id, device_id, audit_entries):
        from .models import MedicationBatch
        uuid = rec.get("uuid")
        if not uuid:
            return
        defaults = {
            "medication_id": rec.get("medication_id"), "supplier_id": rec.get("supplier_id"),
            "batch_number": rec.get("batch_number"), "initial_quantity": rec.get("initial_quantity"),
            "quantity": rec.get("quantity"), "manufacture_date": rec.get("manufacture_date"),
            "expiry_date": rec.get("expiry_date"), "received_date": rec.get("received_date", datetime.now()),
            "quantity_adjustment": rec.get("quantity_adjustment", 0), "updated_at": rec.get("updated_at", datetime.now()),
            "last_sync_device": device_id,
        }
        audit_entries.append({
            "action_type": "SYNC_BATCH", "affected_entity": "MedicationBatch", "entity_pk": uuid,
            "user_identity": device_id,
            "reason": f"Batch synced from device {device_id}",
        })
        MedicationBatch.objects.update_or_create(uuid=uuid, defaults=defaults)

    def _sync_sales_transaction(self, rec, pharmacy_id, device_id, audit_entries):
        from .models import SalesTransaction
        uuid = rec.get("uuid")
        if not uuid:
            return
        defaults = {
            "pharmacy_id": pharmacy_id, "transaction_ref": rec.get("transaction_ref", f"SYNC-{uuid[:6].upper()}"),
            "pharmacist_id": rec.get("pharmacist_id"), "total_amount_naira": rec.get("total_amount_naira", 0.00),
            "payment_method": rec.get("payment_method", "CASH"), "patient_info": rec.get("patient_info", ""),
            "patient_id_or_phone": rec.get("patient_id_or_phone", ""), "prescriber_name": rec.get("prescriber_name", ""),
            "prescriber_reg_no": rec.get("prescriber_reg_no", ""), "health_facility": rec.get("health_facility", ""),
            "notes": rec.get("notes", ""), "updated_at": rec.get("updated_at", datetime.now()),
            "last_sync_device": device_id,
        }
        existing, created = SalesTransaction.objects.get_or_create(uuid=uuid, defaults=defaults)
        if not created:
            existing.total_amount_naira = rec.get("total_amount_naira", existing.total_amount_naira)
            existing.payment_method = rec.get("payment_method", existing.payment_method)
            existing.patient_info = rec.get("patient_info", existing.patient_info)
            existing.last_sync_device = device_id
            existing.updated_at = rec.get("updated_at", datetime.now())
            existing.save()
        audit_entries.append({
            "action_type": "SYNC_SALES_TRANSACTION", "affected_entity": "SalesTransaction", "entity_pk": uuid,
            "user_identity": device_id,
            "reason": f"Sale {'created' if created else 'reconciled'} from device {device_id}",
        })

    def _sync_sales_transaction_item(self, rec, pharmacy_id, device_id, audit_entries):
        from .models import SalesTransactionItem
        uuid = rec.get("uuid")
        if not uuid:
            return
        defaults = {
            "medication_id": rec.get("medication_id"), "quantity_sold": rec.get("quantity_sold"),
            "unit_price_naira": rec.get("unit_price_naira"), "subtotal_naira": rec.get("subtotal_naira", 0),
            "updated_at": rec.get("updated_at", datetime.now()), "last_sync_device": device_id,
        }
        key_fields = {"medication_id": rec.get("medication_id")}
        item, created = SalesTransactionItem.objects.get_or_create(**key_fields, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(item, k, v)
            item.save()
        audit_entries.append({
            "action_type": "SYNC_SALES_ITEM", "affected_entity": "SalesTransactionItem", "entity_pk": f"{uuid or 'item'}",
            "user_identity": device_id,
            "reason": f"Sale item {'created' if created else 'updated'} from device {device_id}",
        })

    def _process_audit_record(self, rec, pharmacy_id, device_id, audit_entries):
        audit_entries.append({
            "action_type": "SYNC_AUDIT_LEDGER", "affected_entity": "StockAuditLedger",
            "entity_pk": rec.get("transaction_id", "unknown"), "user_identity": device_id,
            "reason": f"Audit record received from device {device_id}",
        })


class SyncPullView(View):
    """GET /api/sync/pull/"""

    def get(self, request, *args, **kwargs):
        last_sync_str = request.GET.get("last_sync_timestamp", "")
        try:
            last_sync_ts = datetime.fromisoformat(last_sync_str) if last_sync_str else datetime.min
        except (ValueError, TypeError):
            last_sync_ts = datetime.min

        pharmacy_id = None
        with pharmacy_context():
            pharmacy_id = pharmacy_context.get_current_pharmacy_id()

        if not pharmacy_id:
            return JsonResponse({"records": {}, "pharmacy_id": None})

        since = last_sync_ts if last_sync_ts else datetime.min

        records = {"medication": [], "medicationbatch": [], "salestransaction": [],
                     "salesttransactionitem": [], "stockauditedger": []}

        from .models import Medication, MedicationBatch, SalesTransaction
        medications = Medication.objects.filter(updated_at__gt=since, pharmacy_id=pharmacy_id)
        for m in medications.values("uuid", "name", "sku", "unit", "drug_schedule", "unit_cost",
                                        "selling_price_per_unit", "updated_at"):
            records["medication"].append(dict(m))

        batches = MedicationBatch.objects.filter(updated_at__gt=since, pharmacy_id=pharmacy_id)
        for b in batches.values("uuid", "batch_number", "expiry_date", "quantity", "manufacture_date", "updated_at"):
            records["medicationbatch"].append(dict(b))

        transactions = SalesTransaction.objects.filter(updated_at__gt=since, pharmacy_id=pharmacy_id)
        for t in transactions.values("uuid", "transaction_ref", "total_amount_naira", "payment_method", "updated_at"):
            records["salestransaction"].append(dict(t))

        from .models import StockAuditLedger
        audit_entries = StockAuditLedger.objects.filter(timestamp__gt=since, pharmacy_id=pharmacy_id)
        for a in audit_entries.values("transaction_id", "action_type", "affected_entity", "entity_pk", "timestamp", "user_identity"):
            records["stockauditedger"].append(dict(a))

        return JsonResponse({"records": records, "pharmacy_id": pharmacy_id,
                             "server_timestamp": datetime.utcnow().isoformat() + "Z"})


class SyncStatusView(View):
    """GET /api/sync/status/"""

    def get(self, request, *args, **kwargs):
        from .models import StockAuditLedger
        pharmacy_id = None
        with pharmacy_context():
            pharmacy_id = pharmacy_context.get_current_pharmacy_id()

        if not pharmacy_id:
            return JsonResponse({"status": "Local Offline", "last_sync_timestamp": None})

        last_entry = StockAuditLedger.objects.filter(pharmacy_id=pharmacy_id).order_by('-timestamp').first()
        if last_entry:
            last_ts = last_entry.timestamp
            last_action = last_entry.action_type
        else:
            last_ts = None
            last_action = None

        pending = StockAuditLedger.objects.filter(pharmacy_id=pharmacy_id).count() > 0

        if last_ts:
            status = "Synced"
        elif pending:
            status = "Local Offline"
        else:
            status = "Synced"

        return JsonResponse({
            "status": status, "last_sync_timestamp": last_ts.isoformat() + "Z" if last_ts else None,
            "last_action": last_action, "pharmacy_id": pharmacy_id,
        })
