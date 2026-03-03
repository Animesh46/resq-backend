"""
Notifier Module
Handles: email alerts, SMS fallback, safety loop triggers.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send email notification."""
    if not SMTP_USER or not to:
        logger.warning("SMTP not configured or recipient missing — skipping email")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        logger.info(f"Email sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False


def send_distress_notification(
    contact_email: str,
    contact_phone: str,
    user_name: str,
    lat: float,
    lon: float,
    disaster_type: Optional[str],
    battery: int,
):
    """Send distress alert to emergency contact via email (messaging disabled)."""
    maps_link = f"https://maps.google.com/?q={lat},{lon}"
    disaster_str = disaster_type or "Unknown Emergency"

    email_body = f"""
URGENT: ResQ DISTRESS SIGNAL

{user_name} has activated an emergency distress signal.

Location: {maps_link}
Disaster Type: {disaster_str}
Battery: {battery}%
Please check on them immediately.

This message was automatically sent by ResQ Disaster Intelligence App.
"""
    send_email(contact_email, f"ResQ DISTRESS: {user_name}", email_body)
    if contact_phone:
        logger.warning("Emergency contact phone provided but messaging is disabled")


def send_safety_check_failed(
    contact_email: str,
    contact_phone: str,
    user_name: str,
    lat: float,
    lon: float,
    alert_type: str,
):
    """Sent when user doesn't respond to 'Are You Safe?' within timeout."""
    maps_link = f"https://maps.google.com/?q={lat},{lon}"

    email_body = f"""
ResQ Safety Check — NO RESPONSE

{user_name} was sent a safety check during a {alert_type} alert
but did not respond within the timeout period.

Last Known Location: {maps_link}
Please contact them immediately.

This is an automated message from ResQ.
"""
    send_email(contact_email, f"ResQ Safety Check Failed: {user_name}", email_body)
    if contact_phone:
        logger.warning("Emergency contact phone provided but messaging is disabled")
