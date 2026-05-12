"""Pluggable alert notification dispatchers."""
import asyncio
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.alert import Alert

log = get_logger(__name__)


class NotificationChannel(Protocol):
    async def send(self, alert: Alert) -> bool: ...


class EmailChannel:
    def __init__(self, recipients: list[str]):
        self.recipients = recipients

    async def send(self, alert: Alert) -> bool:
        if not (settings.SMTP_HOST and self.recipients):
            return False
        return await asyncio.to_thread(self._send_sync, alert)

    def _send_sync(self, alert: Alert) -> bool:
        msg = EmailMessage()
        msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
        msg["From"] = settings.SMTP_FROM or "alerts@civil-monitoring.local"
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(
            f"{alert.message}\n\n"
            f"Site: {alert.site_id}\n"
            f"Sensor: {alert.sensor_id}\n"
            f"Triggered value: {alert.triggered_value}\n"
            f"Threshold: {alert.threshold_value}\n"
            f"Time: {alert.ts.isoformat()}\n"
        )
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
                if settings.SMTP_USE_TLS:
                    s.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
            return True
        except Exception as e:
            log.error("email.send_failed", error=str(e))
            return False


class SlackChannel:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        color = {"info": "#3498db", "warning": "#f1c40f", "critical": "#e74c3c"}[alert.severity.value]
        payload = {
            "attachments": [{
                "color": color,
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Category", "value": alert.category.value, "short": True},
                    {"title": "Value", "value": str(alert.triggered_value), "short": True},
                    {"title": "Threshold", "value": str(alert.threshold_value), "short": True},
                ],
                "ts": int(alert.ts.timestamp()),
            }]
        }
        try:
            async with httpx.AsyncClient(timeout=10) as cli:
                r = await cli.post(self.webhook_url, json=payload)
            return r.status_code == 200
        except Exception as e:
            log.error("slack.send_failed", error=str(e))
            return False


class DiscordChannel:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        color_int = {"info": 0x3498db, "warning": 0xf1c40f, "critical": 0xe74c3c}[
            alert.severity.value
        ]
        payload = {
            "embeds": [{
                "title": alert.title,
                "description": alert.message,
                "color": color_int,
                "fields": [
                    {"name": "Severity", "value": alert.severity.value, "inline": True},
                    {"name": "Category", "value": alert.category.value, "inline": True},
                    {"name": "Value", "value": str(alert.triggered_value), "inline": True},
                    {"name": "Threshold", "value": str(alert.threshold_value), "inline": True},
                ],
                "timestamp": alert.ts.isoformat(),
            }]
        }
        try:
            async with httpx.AsyncClient(timeout=10) as cli:
                r = await cli.post(self.webhook_url, json=payload)
            return r.status_code in (200, 204)
        except Exception as e:
            log.error("discord.send_failed", error=str(e))
            return False


def _build_channels() -> list[NotificationChannel]:
    channels: list[NotificationChannel] = []
    if settings.SLACK_WEBHOOK_URL:
        channels.append(SlackChannel(settings.SLACK_WEBHOOK_URL))
    if settings.DISCORD_WEBHOOK_URL:
        channels.append(DiscordChannel(settings.DISCORD_WEBHOOK_URL))
    # NOTE: Email recipients to fetch from site managers in production.
    # For MVP we send only if SMTP_FROM and an admin email is provided via env.
    return channels


async def dispatch_alert_notifications(db: AsyncSession, alert: Alert) -> None:
    channels = _build_channels()
    if not channels:
        return
    results = await asyncio.gather(*(c.send(alert) for c in channels), return_exceptions=True)
    success = any(r is True for r in results)
    if success:
        alert.notified = True
        await db.commit()
