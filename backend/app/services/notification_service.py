from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Twilio SMS/WhatsApp notifications for confirmed critical alerts.

    Errors are caught and logged — a Twilio failure must never block
    the confirm-response sent back to the UI.
    """

    def __init__(self) -> None:
        self._client = None
        self._enabled = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)

    def _get_client(self):
        if self._client is None and self._enabled:
            try:
                from twilio.rest import Client
                self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            except Exception as exc:
                logger.error("Failed to initialise Twilio client", extra={"error": str(exc)})
        return self._client

    async def send_alert_notification(
        self, alert_id: str, zone_name: str, severity: str, recipients: list[str]
    ) -> None:
        """Send SMS notification to a list of phone numbers."""
        if not self._enabled:
            logger.info("Twilio not configured — skipping SMS notification")
            return

        client = self._get_client()
        if not client:
            return

        message_body = (
            f"🚨 SentinelGrid ALERT [{severity.upper()}]\n"
            f"Zone: {zone_name}\n"
            f"Alert ID: {alert_id}\n"
            f"Action required — confirm at your dashboard."
        )

        for recipient in recipients:
            try:
                client.messages.create(
                    body=message_body,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=recipient,
                )
                logger.info("SMS sent", extra={"recipient": recipient, "alert_id": alert_id})
            except Exception as exc:
                logger.error(
                    "Twilio SMS failed",
                    extra={"recipient": recipient, "error": str(exc)},
                )

    async def send_whatsapp_notification(
        self, alert_id: str, zone_name: str, severity: str, recipients: list[str]
    ) -> None:
        """Send WhatsApp message via Twilio sandbox."""
        if not self._enabled:
            return

        client = self._get_client()
        if not client:
            return

        message_body = (
            f"🚨 *SentinelGrid ALERT* [{severity.upper()}]\n"
            f"*Zone:* {zone_name}\n"
            f"*Alert ID:* {alert_id}\n"
            f"Action required — confirm at your dashboard."
        )

        for recipient in recipients:
            try:
                client.messages.create(
                    body=message_body,
                    from_=f"whatsapp:{settings.TWILIO_FROM_NUMBER}",
                    to=f"whatsapp:{recipient}",
                )
            except Exception as exc:
                logger.error("WhatsApp notification failed", extra={"error": str(exc)})


notification_service = NotificationService()
