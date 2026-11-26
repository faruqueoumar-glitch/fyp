import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime
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

DOWNLOADS_DIR = Path.home() / "Downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

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

DESKTOP_BRIDGE_JS = """
(function() {
  if (window.__paDesktopBridgeBound) return;
  window.__paDesktopBridgeBound = true;

  document.addEventListener('keydown', function(e) {
    if (e.altKey && e.key === 'ArrowLeft') window.history.back();
    if (e.altKey && e.key === 'ArrowRight') window.history.forward();
  });

  function showToast(msg, isError) {
    var existing = document.getElementById('__pa_toast');
    if (existing) existing.remove();
    var el = document.createElement('div');
    el.id = '__pa_toast';
    el.textContent = msg;
    el.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:999999;background:' + (isError ? '#b91c1c' : '#0f172a') + ';color:#fff;padding:12px 18px;border-radius:12px;font-family:sans-serif;font-size:13px;font-weight:600;box-shadow:0 10px 25px rgba(0,0,0,0.3);';
    document.body.appendChild(el);
    setTimeout(function() { if (el.parentNode) el.remove(); }, 5000);
  }
  window.__paShowToast = showToast;

  // Intercept CSV / report export links so they save directly to ~/Downloads without triggering PyQt6's broken setPath()
  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[href]');
    if (!link) return;
    var href = link.getAttribute('href') || '';
    if (href.indexOf('export=csv') !== -1 || href.indexOf('/reports/export') !== -1) {
      e.preventDefault();
      e.stopPropagation();
      var fullUrl = new URL(href, window.location.origin).toString();
      showToast('Exporting CSV report...');
      fetch(fullUrl, { credentials: 'same-origin' })
        .then(function(resp) {
          if (!resp.ok) throw new Error('HTTP ' + resp.status);
          var disp = resp.headers.get('Content-Disposition') || '';
          var match = disp.match(/filename="?([^";]+)"?/i);
          var fname = match ? match[1] : ('pharma_report_' + Date.now() + '.csv');
          return resp.text().then(function(text) { return { fname: fname, text: text }; });
        })
        .then(function(data) {
          if (window.pywebview && window.pywebview.api && window.pywebview.api.save_csv_file) {
            return window.pywebview.api.save_csv_file(data.fname, data.text);
          }
        })
        .then(function(savedPath) {
          if (savedPath) showToast('Saved CSV: ' + savedPath);
        })
        .catch(function(err) {
          showToast('CSV Export failed: ' + err.message, true);
        });
    }
  }, true);

  // Override window.print() so Print Receipt & Print ID Card open an auto-printing sheet in the system browser
  window.print = function() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.print_current_page) {
      showToast('Preparing printable document...');
      var html = document.documentElement.outerHTML;
      var baseUrl = window.location.origin;
      window.pywebview.api.print_current_page(html, baseUrl).then(function(savedPath) {
        if (savedPath) {
          showToast('Opened print dialog: ' + savedPath);
        }
      }).catch(function(err) {
        showToast('Print error: ' + err, true);
      });
    }
  };
})();
"""


class DesktopAPI:
    def __init__(self):
        self.window = None

    def save_csv_file(self, filename: str, content: str) -> str:
        safe_name = os.path.basename(filename or f"pharma_export_{int(time.time())}.csv")
        target = DOWNLOADS_DIR / safe_name
        target.write_text(content, encoding="utf-8-sig")
        try:
            subprocess.Popen(["xdg-open", str(target)], start_new_session=True)
        except Exception:
            pass
        return str(target)

    def print_current_page(self, html: str, base_url: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = DOWNLOADS_DIR / f"PharmaAuditOS_Receipt_{ts}.html"
        inject = f'<base href="{base_url}/"><script>window.addEventListener("load", function(){{ setTimeout(function(){{ window.print(); }}, 350); }});</script>'
        if "<head>" in html:
            final_html = html.replace("<head>", "<head>" + inject, 1)
        else:
            final_html = inject + html
        html_path.write_text(final_html, encoding="utf-8")
        subprocess.Popen(["xdg-open", str(html_path)], start_new_session=True)
        return str(html_path)


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


def on_loaded(window):
    try:
        window.evaluate_js(DESKTOP_BRIDGE_JS)
    except Exception:
        pass


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    wait_for_server(LOCAL_URL)

    webview.settings["ALLOW_DOWNLOADS"] = False
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False

    api = DesktopAPI()
    try:
        win = webview.create_window(
            "PharmaAudit OS",
            LOCAL_URL,
            width=1280,
            height=820,
            min_size=(360, 640),
            js_api=api,
        )
        api.window = win
        win.events.loaded += lambda: on_loaded(win)
        webview.start(gui="qt")
    except Exception:
        webbrowser.open(LOCAL_URL)
        server_thread.join()
