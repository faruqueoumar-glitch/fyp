import os
import sys
import threading
import traceback
from pathlib import Path

_started = False
_lock = threading.Lock()
last_error = ""


def start(files_dir: str):
    global _started, last_error
    with _lock:
        if _started:
            return
        _started = True

    try:
        os.environ["HOME"] = files_dir
        os.environ["TMPDIR"] = files_dir
        os.makedirs(files_dir, exist_ok=True)

        base_dir = Path(__file__).resolve().parent / "backend"
        sys.path.insert(0, str(base_dir))
        sys.path.insert(0, str(base_dir / "src"))

        os.environ["PHARMAAUDIT_STANDALONE"] = "1"
        os.environ["PHARMAAUDIT_DATA_DIR"] = files_dir
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings.dev")

        import django
        django.setup()

        from django.core.management import call_command
        from django.core.wsgi import get_wsgi_application
        from waitress import serve

        call_command("migrate", interactive=False)
        application = get_wsgi_application()
        serve(application, host="127.0.0.1", port=8765, threads=4)
    except Exception:
        last_error = traceback.format_exc()
        raise
