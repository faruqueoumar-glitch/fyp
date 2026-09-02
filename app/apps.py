import os
import sys
from django.apps import AppConfig


class PharmacyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Do not start background worker during test suite runs
        if 'test' in sys.argv:
            return

        # Start the keep-alive background thread.
        # In development with auto-reload, RUN_MAIN is set to 'true' on the
        # reloader child process — only start there to avoid duplicate threads.
        # In production (gunicorn/daphne), RUN_MAIN is not set, so we always start.
        run_main = os.environ.get('RUN_MAIN')
        if run_main == 'true' or run_main is None:
            from app.keep_alive import start_render_keep_alive
            start_render_keep_alive()
