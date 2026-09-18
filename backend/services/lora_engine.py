"""
Project Rakshak — LoRa Mesh Engine
Simulates low-power, long-range peer-to-peer RF mesh networking
over India's license-free 865–867 MHz ISM Band.
Provides zero-internet, resilient telemetry and emergency SOS relay
during catastrophic cellular tower & grid blackouts in Himalayan gorges.
"""

import json
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.core.database import get_db

logger = logging.getLogger("rakshak.lora")

# Topology link graph: Source Node -> Next downstream hop toward Gateway
MANDAKINI_MESH_GRAPH = {
    "LORA-ND-01": "LORA-ND-02",  # Kedarnath Ridge -> Lincheli
    "LORA-ND-02": "LORA-ND-03",  # Lincheli -> Rambara
    "LORA-ND-03": "LORA-ND-04",  # Rambara -> Gaurikund
    "LORA-ND-04": "LORA-GW-05",  # Gaurikund -> Sonprayag Gateway
    "LORA-GW-05": "LORA-ND-06",  # Sonprayag -> Guptkashi
    "LORA-ND-06": "LORA-GW-08",  # Guptkashi -> Rudraprayag Central
    "LORA-ND-07": "LORA-GW-08",  # Joshimath -> Rudraprayag Central
    "LORA-GW-08": None,          # Central SEOC Hub
}


def get_all_nodes() -> List[Dict[str, Any]]:
    """Fetch all active Himalayan LoRa mesh nodes with live RF link metrics."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM lora_nodes ORDER BY elevation_m DESC").fetchall()
    nodes = []
    now = datetime.now(timezone.utc).isoformat()

    for r in rows:
        n = dict(r)
        # Simulate slight RF metric variance
        jitter = random.randint(-2, 2)
        n["rssi_dbm"] = max(-115, min(-65, n["rssi_dbm"] + jitter))
        n["next_hop"] = MANDAKINI_MESH_GRAPH.get(n["id"])
        n["is_gateway"] = "GATEWAY" in n["role"]
        nodes.append(n)

    conn.close()
    return nodes


def get_recent_packets(limit: int = 25) -> List[Dict[str, Any]]:
    """Fetch recent decoded LoRa packets."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM lora_packets ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    packets = []
    for r in rows:
        p = dict(r)
        try:
            p["payload"] = json.loads(p["payload_json"])
        except Exception:
            p["payload"] = {}
        packets.append(p)
    conn.close()
    return packets


def transmit_lora_packet(
    source_node_id: str,
    packet_type: str,
    payload: Dict[str, Any],
    max_hops: int = 5
) -> Dict[str, Any]:
    """
    Simulate transmitting an RF packet across the mountain mesh network.
    Trace each hop down the gorge until reaching a Gateway node.
    If it's an SOS_DISTRESS packet, automatically injects into the SEOC triage table.
    """
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Verify source node
    src_node = conn.execute("SELECT * FROM lora_nodes WHERE id=?", (source_node_id,)).fetchone()
    if not src_node:
        conn.close()
        raise ValueError(f"Unknown LoRa node ID: {source_node_id}")

    # Trace mesh hops
    hop_path = [source_node_id]
    curr = source_node_id
    hops = 0
    reached_gateway = False
    gateway_id = None

    while curr and hops < max_hops:
        next_node = MANDAKINI_MESH_GRAPH.get(curr)
        if not next_node:
            # Reached end or gateway
            reached_gateway = True
            gateway_id = curr
            break
        hop_path.append(next_node)
        curr = next_node
        hops += 1

        # Check if next_node is a gateway
        node_row = conn.execute("SELECT role FROM lora_nodes WHERE id=?", (curr,)).fetchone()
        if node_row and "GATEWAY" in node_row["role"]:
            reached_gateway = True
            gateway_id = curr
            break

    packet_hash = f"PKT-{uuid.uuid4().hex[:6].upper()}"
    raw_hex = f"4C4F5241{packet_hash.replace('-', '')}{random.randint(1000, 9999)}"
    rssi = random.randint(-105, -75)
    snr = round(random.uniform(5.0, 11.5), 1)

    # Insert into lora_packets table
    conn.execute("""
        INSERT INTO lora_packets (
            packet_hash, source_node, destination_node, hop_count, max_hops,
            packet_type, payload_json, raw_hex, rssi_dbm, snr_db, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        packet_hash, source_node_id, gateway_id or "LORA-GW-05", len(hop_path) - 1,
        max_hops, packet_type.upper(), json.dumps(payload), raw_hex, rssi, snr, now
    ))

    # Update source node last_seen
    conn.execute("UPDATE lora_nodes SET last_seen=? WHERE id=?", (now, source_node_id))

    sos_created_id = None
    # If this is an emergency SOS packet relayed over LoRa, integrate directly into SEOC triage!
    if packet_type.upper() == "SOS_DISTRESS":
        sos_created_id = f"SOS-LORA-{random.randint(100, 999)}"
        caller_name = payload.get("caller", f"LoRa Beacon {source_node_id}")
        location_name = payload.get("location", f"{src_node['name']} ({src_node['sector']})")
        details = payload.get("details", "Distress beacon relayed via LoRa mesh network (0% cellular fallback).")
        lat = payload.get("lat", src_node["lat"])
        lng = payload.get("lng", src_node["lng"])

        conn.execute("""
            INSERT INTO sos_signals (
                id, caller_name, phone, lat, lng, location_name, details,
                status, assigned_unit, priority, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', 'LoRa Auto-Triage', 'CRITICAL', ?, ?)
        """, (sos_created_id, caller_name, "LORA-MESH-RADIO", lat, lng, location_name, details, now, now))

        # Also log SEOC incident
        conn.execute("""
            INSERT INTO incidents (type, msg, zone, priority, lat, lng, risk_score, created_at)
            VALUES ('SOS_LORA', ?, ?, 'CRITICAL', ?, ?, 95, ?)
        """, (f"[LORA OFFLINE MESH] Distress packet decoded from {source_node_id}: {details}", location_name, lat, lng, now))

        logger.info("[LoRa Mesh] SOS packet %s relayed from %s -> Injected into SEOC triage", packet_hash, source_node_id)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "packet_hash": packet_hash,
        "source_node": source_node_id,
        "gateway_reached": gateway_id,
        "hop_count": len(hop_path) - 1,
        "hop_path": hop_path,
        "transit_latency_ms": (len(hop_path) - 1) * 340 + random.randint(40, 120),
        "rssi_dbm": rssi,
        "snr_db": snr,
        "frequency_mhz": src_node["frequency_mhz"],
        "spreading_factor": src_node["spreading_factor"],
        "sos_id": sos_created_id,
        "packet_type": packet_type.upper(),
        "timestamp": now,
    }
