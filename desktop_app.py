import os
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

DATA_DIR = Path(
    os.environ.get("PHARMAAUDIT_DATA_DIR")
    or (
        Path(os.environ["APPDATA"]) / "PharmaAuditOS"
        if os.name == "nt"
        else Path.home() / ".local" / "share" / "PharmaAuditOS"
    )
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

os.environ["PHARMAAUDIT_STANDALONE"] = "1"
os.environ["PHARMAAUDIT_DATA_DIR"] = str(DATA_DIR)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DATA_DIR / 'db.sqlite3'}")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings.dev")

import django
django.setup()

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from waitress import serve
import webview

HOST = "0.0.0.0"
PORT = 8765
LOCAL_URL = f"http://127.0.0.1:{PORT}"


def start_server():
    call_command("migrate", interactive=False)
    application = get_wsgi_application()
    serve(application, host=HOST, port=PORT, threads=6)


def wait_for_server(url: str, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    wait_for_server(LOCAL_URL)
    try:
        webview.create_window(
            "PharmaAudit OS",
            LOCAL_URL,
            width=1280,
            height=820,
            min_size=(360, 640),
        )
        webview.start(gui="qt")
    except Exception:
        webbrowser.open(LOCAL_URL)
        server_thread.join()
