import os
import sys
from django.apps import AppConfig


class PharmacyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Skip background thread startup during management commands
        skip_commands = ['test', 'makemigrations', 'migrate', 'collectstatic', 'shell', 'check']
        if any(cmd in sys.argv for cmd in skip_commands):
            return

        # Guard: only start background threads under runserver when RUN_MAIN == 'true'
        # (prevents duplicate threads under autoreloader)
        runserver = 'runserver' in sys.argv
        if runserver and os.environ.get('RUN_MAIN') != 'true':
            return

        # Start the keep-alive background thread.
        # In development with auto-reload, RUN_MAIN is set to 'true' on the
        # reloader child process — only start there to avoid duplicate threads.
        # In production (gunicorn/daphne), RUN_MAIN is not set, so we always start.
        run_main = os.environ.get('RUN_MAIN')
        if run_main == 'true' or run_main is None:
            from app.keep_alive import start_render_keep_alive
            start_render_keep_alive()

        # ── Sync Engine startup ──────────────────────────────────────────────
        # Connect pre_save signals for device_id stamping on syncable models
        from .sync_engine import stamp_device_id
        from .models import CustomUser, Medication, MedicationBatch, SalesTransaction, SalesTransactionItem, StockAuditLedger
        for model in [CustomUser, Medication, MedicationBatch, SalesTransaction,
                       SalesTransactionItem, StockAuditLedger]:
            from django.db.models.signals import pre_save
            pre_save.connect(stamp_device_id, sender=model)

        # Start ZeroconfPeerManager and BackgroundSyncWorker
        from .sync_engine import ZeroconfPeerManager, BackgroundSyncWorker
        zeroconf_manager = ZeroconfPeerManager()
        try:
            zeroconf_manager.start()
        except Exception:
            pass

        worker = BackgroundSyncWorker()
        worker.start()
