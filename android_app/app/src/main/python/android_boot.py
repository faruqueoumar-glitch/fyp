import os
import sys
import threading
from pathlib import Path

_started = False
_lock = threading.Lock()


def start(files_dir: str):
    global _started
    with _lock:
        if _started:
            return
        _started = True

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
    serve(application, host="0.0.0.0", port=8765, threads=4)
