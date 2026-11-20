import threading
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    """Send transactional emails via Brevo HTTPS API (port 443) for Render Free."""

    api_url = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        api_key = getattr(settings, "BREVO_API_KEY", None)
        if not api_key:
            logger.error("BREVO_API_KEY is not configured.")
            return 0

        sent_count = 0
        for message in email_messages:
            if not message.to:
                continue

            sender_name, sender_email = parseaddr(
                message.from_email or settings.DEFAULT_FROM_EMAIL
            )
            payload = {
                "sender": {
                    "name": sender_name or "PharmaAudit OS",
                    "email": sender_email,
                },
                "to": [{"email": addr} for addr in message.to],
                "subject": message.subject,
                "textContent": message.body,
            }

            for content, mimetype in getattr(message, "alternatives", []):
                if mimetype == "text/html":
                    payload["htmlContent"] = content
                    break

            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "accept": "application/json",
                    "api-key": api_key,
                    "content-type": "application/json",
                },
                method="POST",
            )

            def _send_async(request_obj):
                try:
                    with urllib.request.urlopen(request_obj, timeout=10) as resp:
                        if not (200 <= resp.status < 300):
                            logger.warning("Brevo API non-2xx status: %s", resp.status)
                except urllib.error.HTTPError as exc:
                    err_body = exc.read().decode("utf-8", errors="ignore")
                    logger.error("Brevo API HTTP %s: %s", exc.code, err_body)
                except Exception as exc:
                    logger.error("Brevo API request failed: %s", exc)

            threading.Thread(target=_send_async, args=(req,), daemon=True).start()
            sent_count += 1

        return sent_count
