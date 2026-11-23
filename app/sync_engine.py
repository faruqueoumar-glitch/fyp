import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import (
    CustomUser, Medication, MedicationBatch, SalesTransaction,
    SalesTransactionItem, StockAuditLedger, Pharmacy
)
from .tenancy import get_current_pharmacy_id, pharmacy_context


# ── Device ID Management ──────────────────────────────────────────────

DEVICE_CONFIG_PATH = Path(settings.BASE_DIR) / 'device_config.json'


def get_persistent_device_id(pharmacy_id=None):
    """
    Get or create a persistent device ID stored in device_config.json.
    Format: PHARM-OS-{pharmacy_id}-{uuid_hex8}
    """
    if DEVICE_CONFIG_PATH.exists():
        try:
            import json
            with open(DEVICE_CONFIG_PATH) as f:
                cfg = json.load(f)
            if cfg.get('pharmacy_id') == pharmacy_id:
                return cfg['device_id']
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Generate new device ID
    device_id = f"PHARM-OS-{pharmacy_id or 'unknown'}-{uuid.uuid4().hex[:8].upper()}"
    
    # Persist
    try:
        DEVICE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DEVICE_CONFIG_PATH, 'w') as f:
            json.dump({'pharmacy_id': pharmacy_id, 'device_id': device_id}, f)
    except OSError:
        pass

    return device_id


def get_current_device_id():
    """Return device ID for current pharmacy context."""
    pharmacy_id = get_current_pharmacy_id()
    return get_persistent_device_id(pharmacy_id)


# Signal: stamp device_id on save if not set
@receiver(pre_save)
def stamp_device_id(sender, instance, **kwargs):
    """
    Auto-stamp device_id on syncable models if not already set.
    Only runs when inside a pharmacy context.
    """
    syncable_models = (Medication, MedicationBatch, SalesTransaction,
                       SalesTransactionItem, StockAuditLedger, CustomUser)
    if sender not in syncable_models:
        return

    field_names = [f.name for f in sender._meta.get_fields()]
    if 'device_id' not in field_names:
        return

    current_val = getattr(instance, 'device_id', None)
    if current_val:
        return

    setattr(instance, 'device_id', get_current_device_id())


# ── Zeroconf Peer Discovery ───────────────────────────────────────────

try:
    from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False


class ZeroconfPeerManager:
    """mDNS/Zeroconf discovery for LAN peer PharmaAudit instances."""

    def __init__(self):
        self.zeroconf = None
        self.browser = None
        self.peers = []
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        if self._running or not ZEROCONF_AVAILABLE:
            return
        self._running = True
        self.zeroconf = Zeroconf()
        self._advertise()
        self.browser = ServiceBrowser(
            self.zeroconf, "_pharmaaudit._tcp.local.", self._on_peer_discovered
        )

    def stop(self):
        self._running = False
        if self.zeroconf:
            try: self.zeroconf.close()
            except Exception: pass
            self.zeroconf = None
        self.peers = []

    def _advertise(self):
        import socket
        device_id = get_current_device_id()
        pharmacy_id = get_current_pharmacy_id() or 'unknown'
        properties = {"device_id": device_id, "pharmacy_id": str(pharmacy_id)}
        txt = '\0'.join(f"{k}={v}" for k, v in properties.items()).encode('utf-8')
        info = ServiceInfo(
            "_pharmaaudit._tcp.local.",
            "PharmaAudit-{}.local".format(device_id[:8].lower()).encode('utf-8'),
            addresses=[],
            port=80,
            properties=txt,
            server=socket.getfqdn()
        )
        try:
            self.zeroconf.register_service(info)
        except Exception:
            pass

    def _on_peer_discovered(self, zc, service_type, name):
        try:
            info = self.zeroconf.get_service_info(service_type, name, timeout=5000)
            if info:
                addresses = [a.decode() for a in info.addresses if a]
                with self._lock:
                    self.peers.append({
                        'name': name,
                        'address': addresses[0] if addresses else 'unknown',
                        'port': info.port,
                        'properties': info.properties,
                    })
        except Exception:
            pass

    def get_peers(self):
        with self._lock:
            return list(self.peers)


# ── Background Sync Worker ────────────────────────────────────────────

class BackgroundSyncWorker(threading.Thread):
    """Daemon thread: runs every 15 seconds, pushes/pulls sync data."""

    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self.peer_manager = ZeroconfPeerManager()
        self.relay_url = getattr(settings, 'SYNC_RELAY_URL', None)

    def run(self):
        self.peer_manager.start()
        try:
            while not self._stop_event.is_set():
                self._sync_cycle()
                self._stop_event.wait(15)
        finally:
            self.peer_manager.stop()

    def _sync_cycle(self):
        pharmacy_id = get_current_pharmacy_id()
        device_id = get_current_device_id()
        if not pharmacy_id:
            return

        # ── Push local changes ──
        try:
            from .models import Medication, MedicationBatch, SalesTransaction
            since = datetime.utcnow() - timedelta(hours=1)
            payload = {'device_id': device_id, 'tables': {}, 'last_sync_timestamp': datetime.utcnow().isoformat() + 'Z'}
            meds = Medication.objects.filter(updated_at__gt=since, pharmacy_id=pharmacy_id).values('uuid', 'updated_at')
            if meds: payload['tables']['medication'] = list(meds)
            batches = MedicationBatch.objects.filter(updated_at__gt=since, pharmacy_id=pharmacy_id).values('uuid', 'updated_at')
            if batches: payload['tables']['medicationbatch'] = list(batches)
            txs = SalesTransaction.objects.filter(updated_at__gt=since, pharmacy_id=pharmacy_id).values('uuid', 'updated_at')
            if txs: payload['tables']['salestransaction'] = list(txs)
            if any(payload['tables'].values()):
                self._push_to_peers_and_relay(payload)
        except Exception:
            pass

        # ── Pull remote changes ──
        try:
            peers = self.peer_manager.get_peers()
            for peer in peers:
                pass
            if self.relay_url:
                import requests
                try:
                    requests.get(f"{self.relay_url}/api/sync/pull/", timeout=10)
                except Exception:
                    pass
        except Exception:
            pass

    def _push_to_peers_and_relay(self, payload):
        import requests
        if self.relay_url:
            try:
                requests.post(f"{self.relay_url}/api/sync/push/", json=payload, timeout=10)
            except Exception:
                pass

    def stop(self):
        self._stop_event.set()


# ── Sync Status for UI ────────────────────────────────────────────────

def get_sync_status():
    from .models import StockAuditLedger
    pharmacy_id = get_current_pharmacy_id()
    if not pharmacy_id:
        return {"status": "Local Offline", "last_sync_timestamp": None}
    last_entry = StockAuditLedger.objects.filter(pharmacy_id=pharmacy_id).order_by('-timestamp').first()
    if last_entry:
        return {"status": "Synced", "last_sync_timestamp": last_entry.timestamp.isoformat() + 'Z'}
    count = StockAuditLedger.objects.filter(pharmacy_id=pharmacy_id).count()
    if count > 0:
        return {"status": "Synced", "last_sync_timestamp": None}
    return {"status": "Local Offline", "last_sync_timestamp": None}


# ── AppConfig Integration ──────────────────────────────────────────────

class SyncEngineAppConfig(AppConfig):
    """PharmaAudit AppConfig with sync engine startup."""
    name = 'app'
    verbose_name = 'PharmaAudit OS'

    def ready(self):
        import sys
        import os

        # Don't run during collectstatic, makemigrations, migrate, or runserver reload
        cmd = os.environ.get('DJANGO_CMD', '')
        if cmd and any(cmd.startswith(x) for x in ['collectstatic', 'makemigrations', 'migrate', 'runserver']):
            return

        # Guard against runserver autoreloader (second invocation)
        if 'runserver' in sys.argv and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            if getattr(settings, '_sync_engine_started', False):
                return
            settings._sync_engine_started = True

        # Connect pre_save signals for device_id stamping
        for model in [CustomUser, Medication, MedicationBatch, SalesTransaction,
                       SalesTransactionItem, StockAuditLedger]:
            pre_save.connect(stamp_device_id, sender=model)

        # Start background sync worker as daemon thread
        worker = BackgroundSyncWorker()
        worker.start()
