"""
================================================================================
          RAKSHAK SEOC BACKEND  --  sentinel_service.py
  The Autonomous Sentinel System: Proactive Disaster Intelligence Daemon
================================================================================

Proactively scans predefined high-risk Himalayan zones on a scheduled interval
using the Rakshak AI Agent. If Severe or Critical threats are detected:
1. Emits a massive high-priority rich terminal alarm with sirens.
2. Autonomously registers active alerts in the SEOC database (incidents & broadcasts).
3. Broadcasts real-time emergency packets over WebSockets to command centers.
4. Dispatches VAPID Web Push to citizen mobile devices.
5. Transmits LoRa RF mesh emergency broadcasts across mountain relays.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Rich Terminal UI components
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Safe stdout handling for Windows to prevent UTF-8 / charmap encoding errors
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        elif hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        elif hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger("rakshak.sentinel")

# Initialize Rich Console with safe Windows legacy handling
console = Console(force_terminal=True, legacy_windows=False)

# ── Monitored High-Risk Zones ─────────────────────────────────────────────────
HIGH_RISK_ZONES: List[str] = [
    "Kedarnath, Uttarakhand",
    "Joshimath, Uttarakhand",
    "Pithoragarh, Uttarakhand",
]

# Coordinates for geospatial mapping & incident registration
ZONE_COORDINATES: Dict[str, Dict[str, float]] = {
    "Kedarnath, Uttarakhand": {"lat": 30.7346, "lng": 79.0669},
    "Joshimath, Uttarakhand": {"lat": 30.5506, "lng": 79.5660},
    "Pithoragarh, Uttarakhand": {"lat": 29.5829, "lng": 80.2182},
}

# ── In-Memory Sentinel Cache ──────────────────────────────────────────────────
_sentinel_cache: Dict[str, Any] = {
    "status": "idle",  # "idle" | "scanning" | "error"
    "last_scan_timestamp": None,
    "last_scan_duration_secs": 0.0,
    "total_scans_completed": 0,
    "scheduler_running": False,
    "interval_hours": 1,
    "high_risk_zones": list(HIGH_RISK_ZONES),
    "scanned_zones": {},
    "active_threats": [],
}

_sentinel_scheduler: Optional[AsyncIOScheduler] = None
_scan_lock = asyncio.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# RICH TERMINAL WARNING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def log_severe_threat_terminal(zone: str, assessment: Dict[str, Any]) -> None:
    """
    Renders an unmistakable, massive red emergency warning in the console
    with sirens, active hazard breakdowns, and action directives.
    """
    try:
        threat_level = str(assessment.get("threat_level", "SEVERE")).upper()
        confidence = str(assessment.get("confidence", "HIGH")).upper()
        summary = str(assessment.get("summary", "No details provided."))
        hazards = assessment.get("active_hazards", [])
        hazard_str = ", ".join(hazards) if hazards else "Unspecified High-Impact Disaster"
        action_plan = assessment.get("action_plan", [])
        rn = assessment.get("resources_needed", {})
        agencies = ", ".join(assessment.get("contact_agencies", [])) or "NDRF, SDRF, SEOC"

        # Construct Rich Emergency Alert Panel
        content = Text()
        content.append("🚨 🚨 🚨  AUTONOMOUS SENTINEL: SEVERE THREAT DETECTED  🚨 🚨 🚨\n\n", style="bold blink bright_red")

        content.append("● TARGET ZONE:        ", style="bold white")
        content.append(f"{zone}\n", style="bold bright_yellow")

        content.append("● THREAT LEVEL:       ", style="bold white")
        content.append(f"{threat_level}\n", style="bold white on red")

        content.append("● CONFIDENCE RATING:  ", style="bold white")
        content.append(f"{confidence}\n", style="bold cyan")

        content.append("● ACTIVE HAZARDS:     ", style="bold white")
        content.append(f"{hazard_str}\n\n", style="bold bright_red")

        content.append("SITUATIONAL OVERVIEW:\n", style="bold underline white")
        content.append(f"{summary}\n\n", style="italic bright_white")

        if action_plan:
            content.append("PRIORITY ACTION DIRECTIVES:\n", style="bold underline bright_yellow")
            for idx, act in enumerate(action_plan, start=1):
                content.append(f"  {idx}. {act}\n", style="bold yellow")
            content.append("\n")

        content.append("RESOURCES REQUIRED:   ", style="bold white")
        content.append(
            f"NDRF: {rn.get('ndrf_teams', 0)} | Helicopters: {rn.get('helicopters', 0)} | "
            f"Medical: {rn.get('medical_units', 0)} | Relief Camps: {rn.get('relief_camps', 0)}\n",
            style="bold magenta",
        )

        content.append("COORDINATING AGENCIES: ", style="bold white")
        content.append(f"{agencies}\n\n", style="bold green")

        content.append(
            "⚡ AUTONOMOUS ACTION TAKEN: Registered in SEOC Database, WebSocket broadcasted, "
            "WebPush dispatched to mobile devices, and LoRa mesh triggered.",
            style="bold bright_cyan",
        )

        panel = Panel(
            content,
            title="[bold bright_red]🚨 RAKSHAK AUTONOMOUS SENTINEL PROTOCOL 🚨[/bold bright_red]",
            subtitle="[bold bright_yellow]AUTOMATIC SEOC THREAT ESCALATION ACTIVE[/bold bright_yellow]",
            border_style="bold bright_red",
            padding=(1, 2),
        )

        console.print("\n")
        console.print(panel)
        console.print("\n")

    except Exception as exc:
        # Fallback to standard logging if Rich formatting encounters terminal issues
        logger.critical(
            "[SENTINEL CRITICAL ALARM] Zone: %s | Threat: %s | Summary: %s (Rich err: %s)",
            zone, assessment.get("threat_level"), assessment.get("summary"), exc
        )


# ─────────────────────────────────────────────────────────────────────────────
# AUTONOMOUS ALERT CREATION & MULTI-CHANNEL BROADCAST
# ─────────────────────────────────────────────────────────────────────────────

async def create_sentinel_alert(zone: str, assessment: Dict[str, Any]) -> Optional[int]:
    """
    Registers a new active emergency alert in the database and broadcasts it across:
    1. incidents table in SQLite (SEOC Command Center Dashboard)
    2. broadcasts table in SQLite (Official Public Broadcast Record)
    3. Live WebSocket broadcast (/ws/live)
    4. VAPID Web Push notifications to enrolled citizen smartphones
    5. LoRa RF mesh packet broadcast to mountain relay nodes
    """
    now = datetime.now(timezone.utc).isoformat()
    threat_level = str(assessment.get("threat_level", "SEVERE")).upper()
    summary = assessment.get("summary", "Severe disaster condition detected by autonomous sentinel.")
    coords = ZONE_COORDINATES.get(zone, {"lat": 30.5, "lng": 79.5})
    incident_id: Optional[int] = None

    # 1. Database incident registration
    try:
        from backend.core.database import get_db

        conn = get_db()
        c = conn.cursor()

        # Insert into incidents table
        c.execute("""
            INSERT INTO incidents (type, msg, zone, priority, lat, lng, risk_score, ai_analysis, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"SENTINEL_{threat_level}",
            f"[AUTONOMOUS SENTINEL {threat_level}] {zone}: {summary}",
            zone,
            "CRITICAL" if threat_level in ("SEVERE", "CRITICAL") else "HIGH",
            coords.get("lat"),
            coords.get("lng"),
            98 if threat_level == "CRITICAL" else 92,
            json.dumps(assessment),
            now,
        ))
        incident_id = c.lastrowid

        # Insert into broadcasts table
        c.execute("""
            INSERT INTO broadcasts (target_city, risk_level, msg_english, channels, operator_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            zone,
            threat_level,
            f"AUTONOMOUS SENTINEL ALERT: {summary}",
            json.dumps(["Autonomous Sentinel", "Web Push", "LoRa RF Mesh", "WebSocket"]),
            "RAKSHAK-SENTINEL-AGENT",
            now,
        ))

        conn.commit()
        conn.close()
        logger.info("Sentinel alert successfully logged to DB (Incident ID: %s)", incident_id)

    except Exception as exc:
        logger.error("Failed to write sentinel alert to database: %s", exc)

    # 2. Real-time WebSocket broadcast to open command center dashboards & citizen tabs
    try:
        from backend.tasks.background import _broadcast_ws

        await _broadcast_ws({
            "type": "emergency_broadcast",
            "title": f"🚨 AUTONOMOUS SENTINEL: {zone}",
            "body": summary,
            "incident_id": incident_id,
            "threat_level": threat_level,
            "location": zone,
            "timestamp": now,
        })
        logger.info("Sentinel WebSocket alert packet broadcasted to active clients.")
    except Exception as exc:
        logger.warning("Sentinel WebSocket broadcast error: %s", exc)

    # 3. Dispatches VAPID Web Push notifications to enrolled citizen phones
    try:
        from backend.core.push_service import send_push_to_all

        await asyncio.to_thread(
            send_push_to_all,
            title=f"🚨 SEOC SENTINEL: {zone} [{threat_level}]",
            body=summary[:180],
            url="/alerts.html",
            priority="CRITICAL",
        )
        logger.info("Sentinel VAPID push notification dispatched to mobile devices.")
    except Exception as exc:
        logger.warning("Sentinel VAPID push error: %s", exc)

    # 4. LoRa RF mesh fallback broadcast to Himalayan relay nodes
    try:
        from backend.services.lora_engine import broadcast_lora_mesh

        lora_msg = f"SENTINEL {zone}: {threat_level} - {summary[:80]}"
        broadcast_lora_mesh(lora_msg, priority="CRITICAL")
        logger.info("Sentinel LoRa mesh broadcast sent across ISM relay nodes.")
    except Exception as exc:
        logger.warning("Sentinel LoRa mesh error: %s", exc)

    return incident_id


# ─────────────────────────────────────────────────────────────────────────────
# CORE SENTINEL SCAN CYCLE
# ─────────────────────────────────────────────────────────────────────────────

async def run_sentinel_cycle() -> Dict[str, Any]:
    """
    Executes a complete proactive scan cycle over all defined high-risk zones.
    Runs non-blocking via asyncio and thread pools.
    """
    from backend.services.agent_service import run_disaster_analysis

    # Avoid overlapping runs
    if _scan_lock.locked():
        logger.info("Sentinel scan cycle is already in progress, skipping duplicate invocation.")
        return _sentinel_cache

    async with _scan_lock:
        t_start = asyncio.get_event_loop().time()
        _sentinel_cache["status"] = "scanning"
        cycle_threats: List[Dict[str, Any]] = []

        logger.info(
            "==============================================================\n"
            "  [SENTINEL] Initiating proactive risk scan across high-risk zones\n"
            "  Zones: %s\n"
            "==============================================================",
            ", ".join(HIGH_RISK_ZONES)
        )

        for zone in HIGH_RISK_ZONES:
            try:
                logger.info("Sentinel scanning target zone: '%s'...", zone)

                # Delegate synchronous LLM & search execution to a worker thread
                assessment: Dict[str, Any] = await asyncio.to_thread(
                    run_disaster_analysis,
                    location=zone,
                    verbose=False,
                )

                # Cache zone assessment
                _sentinel_cache["scanned_zones"][zone] = {
                    "assessment": assessment,
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                }

                tl = str(assessment.get("threat_level", "")).strip().lower()

                # Threat trigger logic: Check for Severe or Critical threat levels
                if tl in ("severe", "critical"):
                    logger.warning("[SENTINEL THREAT DETECTED] Zone: '%s' | Threat Level: %s", zone, tl.upper())
                    cycle_threats.append({
                        "zone": zone,
                        "threat_level": assessment.get("threat_level"),
                        "summary": assessment.get("summary"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                    # 1. Trigger Rich terminal warning
                    log_severe_threat_terminal(zone, assessment)

                    # 2. Trigger auto-alert creation & multi-channel broadcast
                    await create_sentinel_alert(zone, assessment)
                else:
                    logger.info("Zone '%s' status: %s (Confidence: %s)", zone, assessment.get("threat_level"), assessment.get("confidence"))

            except Exception as exc:
                logger.error("Sentinel failed to analyze zone '%s': %s", zone, exc)
                _sentinel_cache["scanned_zones"][zone] = {
                    "error": str(exc),
                    "scanned_at": datetime.now(timezone.utc).isoformat(),
                }

            # Gentle breathing pause between zones to respect remote rate limits
            await asyncio.sleep(2.0)

        elapsed = asyncio.get_event_loop().time() - t_start
        now_iso = datetime.now(timezone.utc).isoformat()

        _sentinel_cache["status"] = "idle"
        _sentinel_cache["last_scan_timestamp"] = now_iso
        _sentinel_cache["last_scan_duration_secs"] = round(elapsed, 2)
        _sentinel_cache["total_scans_completed"] += 1
        _sentinel_cache["active_threats"] = cycle_threats

        logger.info(
            "Sentinel scan cycle completed in %.2fs. Total threats detected: %d",
            elapsed, len(cycle_threats)
        )

        return _sentinel_cache


# ─────────────────────────────────────────────────────────────────────────────
# STATUS QUERY & ON-DEMAND TRIGGER
# ─────────────────────────────────────────────────────────────────────────────

def get_sentinel_status() -> Dict[str, Any]:
    """Returns the latest cached autonomous scan results and metadata."""
    return {
        "status": _sentinel_cache.get("status", "idle"),
        "last_scan_timestamp": _sentinel_cache.get("last_scan_timestamp"),
        "last_scan_duration_secs": _sentinel_cache.get("last_scan_duration_secs", 0.0),
        "total_scans_completed": _sentinel_cache.get("total_scans_completed", 0),
        "scheduler_running": _sentinel_cache.get("scheduler_running", False),
        "interval_hours": _sentinel_cache.get("interval_hours", 1),
        "monitored_zones": list(HIGH_RISK_ZONES),
        "active_threats": list(_sentinel_cache.get("active_threats", [])),
        "scanned_zones": _sentinel_cache.get("scanned_zones", {}),
    }


async def trigger_sentinel_scan() -> Dict[str, Any]:
    """Manually triggers an immediate sentinel scan cycle."""
    return await run_sentinel_cycle()


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER LIFECYCLE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def start_sentinel_scheduler() -> AsyncIOScheduler:
    """
    Initializes and starts the APScheduler AsyncIOScheduler to run the
    sentinel scan every 1 hour in the background.
    """
    global _sentinel_scheduler

    if _sentinel_scheduler is not None and _sentinel_scheduler.running:
        logger.info("Sentinel scheduler is already running.")
        return _sentinel_scheduler

    _sentinel_scheduler = AsyncIOScheduler()

    # Schedule run_sentinel_cycle every 1 hour
    _sentinel_scheduler.add_job(
        run_sentinel_cycle,
        trigger=IntervalTrigger(hours=1),
        id="sentinel_hourly_scan",
        name="Autonomous Sentinel High-Risk Zones Scan",
        replace_existing=True,
        max_instances=1,
    )

    _sentinel_scheduler.start()
    _sentinel_cache["scheduler_running"] = True
    logger.info("[OK] APScheduler: Autonomous Sentinel daemon scheduled every 1 hour.")

    return _sentinel_scheduler


def shutdown_sentinel_scheduler() -> None:
    """Stops the Sentinel APScheduler cleanly during application shutdown."""
    global _sentinel_scheduler
    if _sentinel_scheduler and _sentinel_scheduler.running:
        _sentinel_scheduler.shutdown(wait=False)
        _sentinel_cache["scheduler_running"] = False
        logger.info("[OK] APScheduler: Autonomous Sentinel daemon shutdown completed.")
