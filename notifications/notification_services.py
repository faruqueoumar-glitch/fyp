import logging
import threading
import json
import os
import urllib.request
import urllib.error
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from .models import Notification

logger = logging.getLogger(__name__)

# Credentials & Config (using Django settings as primary source, fallback to environment, and then hardcoded fallback)
QSTACK_NOTIFICATION_API_KEY = getattr(settings, "QSTACK_NOTIFICATION_API_KEY", None) or os.getenv("QSTACK_NOTIFICATION_API_KEY")
QSTACK_NOTIFICATION_SERVER_URL = getattr(settings, "QSTACK_NOTIFICATION_SERVER_URL", None) or os.getenv("QSTACK_NOTIFICATION_SERVER_URL")

class NotificationService:
    
    @staticmethod
    def _post_push_request(title, body, payload, channel=None):
        """
        Helper method executed in a background thread to make the HTTP POST call via urllib.
        """
        try:
            json_data = {
                "channel": channel or "default",
                "title": title,
                "body": body,
                "payload": payload or {}
            }
            data_bytes = json.dumps(json_data).encode('utf-8')
            req = urllib.request.Request(
                QSTACK_NOTIFICATION_SERVER_URL,
                data=data_bytes,
                headers={
                    "X-API-Key": QSTACK_NOTIFICATION_API_KEY,
                    "Content-Type": "application/json",
                    "User-Agent": "PharmaAuditOS/1.0"
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8')
                logger.info("Successfully pushed external notification.")
                return json.loads(res_body) if res_body else {}
        except Exception as e:
            logger.error(f"Failed to send external push: {e}")
            return {"error": str(e)}

    @staticmethod
    def send_external_push(title="System Alert", body="Inventory update alert.", payload=None, channel=None):
        """
        Sends an external push notification. Spawns a background thread to make it non-blocking.
        """
        thread = threading.Thread(
            target=NotificationService._post_push_request,
            args=(title, body, payload, channel)
        )
        thread.daemon = True
        thread.start()

    @staticmethod
    def send_notification(recipient, actor, title, message, target_obj, category='system_alert', type='info'):
        """
        Sends a single notification to one user, saves it in Django DB, and pushes to external widget.
        """
        if recipient == actor:
            return None 

        # 1. Create the Local Django Notification record
        notification = Notification.objects.create(
            recipient=recipient,
            actor=actor,
            title=title,
            message=message,
            target=target_obj,
            category=category,
            type=type
        )

        # 2. Push to microservice
        NotificationService.send_external_push(
            title=title,
            body=message,
            payload={
                "notification_id": str(notification.id),
                "category": category,
                "type": type,
                "recipient": recipient.email,
                "actor": actor.email if actor else "System",
            }
        )
        
        return notification

    @staticmethod
    def send_bulk_notification(recipients, actor, title, message, target_obj, category='system_alert'):
        """
        Creates bulk database records and sends push notifications to multiple users.
        """
        valid_recipients = [u for u in recipients if u != actor]
        if not valid_recipients:
            return []

        content_type = ContentType.objects.get_for_model(target_obj) if target_obj else None
        object_id = target_obj.id if target_obj else None
        
        notifications = [
            Notification(
                recipient=user,
                actor=actor,
                title=title,
                message=message,
                content_type=content_type,
                object_id=object_id,
                category=category
            ) for user in valid_recipients
        ]
        
        created_notifications = Notification.objects.bulk_create(notifications)

        # Send push notifications for each recipient asynchronously
        for notification in created_notifications:
            NotificationService.send_external_push(
                title=title,
                body=message,
                payload={
                    "notification_id": str(notification.id),
                    "category": category,
                    "recipient": notification.recipient.email,
                    "actor": actor.email if actor else "System",
                }
            )

        return created_notifications
