"""
Distress Router
POST /api/distress/sos         → trigger SOS, notify emergency contact
POST /api/distress/safe        → user confirms they are safe
POST /api/distress/check-loop  → backend checks pending safety loops
"""

import asyncio
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks

from models import DistressPayload, SafetyResponse
from modules.notifier import send_distress_notification, send_safety_check_failed
from modules import state
from config import SAFETY_LOOP_TIMEOUT

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sos")
async def trigger_sos(payload: DistressPayload, background_tasks: BackgroundTasks):
    """
    Red distress button handler.
    Collects GPS, battery, disaster type → notifies emergency contact.
    """
    logger.warning(
        f"SOS from {payload.user_name} at ({payload.latitude},{payload.longitude}), "
        f"battery={payload.battery_percent}%, disaster={payload.disaster_type}"
    )

    background_tasks.add_task(
        send_distress_notification,
        payload.emergency_contact_email,
        payload.emergency_contact_phone,
        payload.user_name,
        payload.latitude,
        payload.longitude,
        payload.disaster_type,
        payload.battery_percent,
    )

    # Store for retry tracking
    state.pending_distress.append({
        "user_name": payload.user_name,
        "lat": payload.latitude,
        "lon": payload.longitude,
        "timestamp": payload.timestamp,
        "notified": True,
        "contact_email": payload.emergency_contact_email,
        "contact_phone": payload.emergency_contact_phone,
    })

    return {
        "status": "sent",
        "message": "Distress signal sent to your emergency contact.",
        "timestamp": payload.timestamp,
        "offline_sms": _build_offline_sms(payload),
    }


@router.post("/safety-check")
async def initiate_safety_check(
    user_id: str,
    alert_id: str,
    contact_email: str,
    contact_phone: str,
    user_name: str,
    lat: float,
    lon: float,
    disaster_type: str,
):
    """
    Initiate 'Are You Safe?' loop.
    After SAFETY_LOOP_TIMEOUT minutes with no response, triggers notification.
    """
    state.safety_loops[user_id] = {
        "alert_id": alert_id,
        "sent_at": datetime.utcnow().isoformat(),
        "responded": False,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "user_name": user_name,
        "lat": lat,
        "lon": lon,
        "disaster_type": disaster_type,
    }
    return {"status": "waiting", "timeout_minutes": SAFETY_LOOP_TIMEOUT}


@router.post("/safe")
async def confirm_safe(response: SafetyResponse):
    """User confirms they are safe — cancels the safety loop."""
    loop = state.safety_loops.get(response.user_id)
    if loop:
        loop["responded"] = True
        logger.info(f"{response.user_id} confirmed safe for alert {response.alert_id}")
    return {"status": "confirmed", "message": "Glad you're safe! Stay alert."}


@router.post("/check-loop")
async def check_expired_safety_loops(background_tasks: BackgroundTasks):
    """
    Should be called by a scheduler every minute.
    Sends notifications for unresponded safety checks past timeout.
    """
    timeout = timedelta(minutes=SAFETY_LOOP_TIMEOUT)
    now = datetime.utcnow()
    triggered = []

    for user_id, loop in state.safety_loops.items():
        if loop["responded"]:
            continue
        sent_at = datetime.fromisoformat(loop["sent_at"])
        if now - sent_at > timeout:
            background_tasks.add_task(
                send_safety_check_failed,
                loop["contact_email"],
                loop["contact_phone"],
                loop["user_name"],
                loop["lat"],
                loop["lon"],
                loop["disaster_type"],
            )
            loop["responded"] = True  # Prevent repeat sends
            triggered.append(user_id)

    return {"triggered_notifications": triggered}


def _build_offline_sms(payload: DistressPayload) -> str:
    """
    Pre-built SMS string for offline fallback.
    The mobile app sends this directly via SMS when internet is unavailable.
    """
    maps_link = f"https://maps.google.com/?q={payload.latitude},{payload.longitude}"
    return (
        f"RESQ EMERGENCY: {payload.user_name} needs help! "
        f"Disaster: {payload.disaster_type or 'Unknown'}. "
        f"Battery: {payload.battery_percent}%. "
        f"Location: {maps_link}"
    )
