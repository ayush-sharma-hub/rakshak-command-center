"""
Project Rakshak - Uttarakhand SEOC
Web Push Notification Service (VAPID & Background Wake-up)
"""

import os
import json
import logging
import threading
from typing import Optional
from datetime import datetime, timezone

from py_vapid import Vapid, b64urlencode
from cryptography.hazmat.primitives import serialization
from pywebpush import webpush, WebPushException

from backend.core.database import get_db

logger = logging.getLogger("rakshak.push")

# Path to persistent VAPID private key
VAPID_PEM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vapid_private.pem")
VAPID_CLAIMS = {
    "sub": "mailto:seoc-alert@uttarakhand.gov.in"
}

_vapid_instance: Optional[Vapid] = None
_vapid_public_b64: Optional[str] = None


def get_vapid_keys() -> tuple[Vapid, str]:
    """Load or generate the persistent VAPID keypair."""
    global _vapid_instance, _vapid_public_b64
    if _vapid_instance is not None and _vapid_public_b64 is not None:
        return _vapid_instance, _vapid_public_b64

    if not os.path.exists(VAPID_PEM_PATH):
        v = Vapid()
        v.generate_keys()
        with open(VAPID_PEM_PATH, "wb") as f:
            f.write(v.private_pem())
        _vapid_instance = v
    else:
        _vapid_instance = Vapid.from_file(VAPID_PEM_PATH)

    raw_pub = _vapid_instance.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint
    )
    b64 = b64urlencode(raw_pub)
    _vapid_public_b64 = b64.decode("utf-8") if isinstance(b64, bytes) else str(b64)
    return _vapid_instance, _vapid_public_b64


def get_vapid_public_key() -> str:
    """Return the base64url encoded VAPID public key for frontend push subscription."""
    _, pub_key = get_vapid_keys()
    return pub_key


def _dispatch_push_worker(title: str, body: str, url: str, priority: str):
    """Background worker that pushes to all registered phone endpoints."""
    try:
        _, _ = get_vapid_keys()
        conn = get_db()
        rows = conn.execute("SELECT id, endpoint, p256dh, auth, device_info FROM push_subscriptions").fetchall()

        if not rows:
            conn.close()
            return

        payload_json = json.dumps({
            "title": title,
            "body": body,
            "url": url,
            "priority": priority,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        dead_subscription_ids = []
        sent_count = 0

        for r in rows:
            endpoint = r["endpoint"]
            p256dh = r["p256dh"]
            auth = r["auth"]

            # Skip dummy or simulation subscriptions that aren't valid HTTP endpoints
            if not endpoint or not endpoint.startswith("http"):
                continue

            sub_info = {
                "endpoint": endpoint,
                "keys": {
                    "p256dh": p256dh,
                    "auth": auth
                }
            }

            try:
                webpush(
                    subscription_info=sub_info,
                    data=payload_json,
                    vapid_private_key=VAPID_PEM_PATH,
                    vapid_claims=VAPID_CLAIMS,
                    timeout=5,
                    ttl=120  # Keep alert alive for 2 minutes on push server if phone is momentarily offline
                )
                sent_count += 1
            except WebPushException as ex:
                status_code = getattr(ex.response, "status_code", None) if hasattr(ex, "response") else None
                # If phone unregistered or subscription expired, prune it
                if status_code in (404, 410):
                    dead_subscription_ids.append(r["id"])
                logger.warning(f"WebPush failed for device {r['id']}: {ex}")
            except Exception as ex:
                logger.warning(f"General push error for device {r['id']}: {ex}")

        # Prune expired subscriptions
        if dead_subscription_ids:
            placeholders = ",".join("?" * len(dead_subscription_ids))
            conn.execute(f"DELETE FROM push_subscriptions WHERE id IN ({placeholders})", dead_subscription_ids)
            conn.commit()

        conn.close()
        logger.info(f"Dispatched emergency push notification to {sent_count} active phones.")
    except Exception as e:
        logger.error(f"Error in push worker: {e}")


def send_push_to_all(title: str, body: str, url: str = "/map.html", priority: str = "CRITICAL"):
    """
    Non-blocking push dispatcher.
    Spawns background thread so admin API response is instantaneous.
    """
    thread = threading.Thread(
        target=_dispatch_push_worker,
        args=(title, body, url, priority),
        daemon=True
    )
    thread.start()
