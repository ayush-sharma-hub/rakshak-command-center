"""
Project Rakshak - Uttarakhand SEOC
SQLite Database Schema, Initialization, and Connection Manager
"""

import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rakshak.db")


def get_db() -> sqlite3.Connection:
    """Returns a new SQLite connection with Row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Better concurrent read/write
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables and seed initial data if empty."""
    conn = get_db()
    c = conn.cursor()

    # ─── 1. FIELD UNITS TABLE ─────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS field_units (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            callsign TEXT NOT NULL,
            unit_type TEXT NOT NULL,  -- NDRF / SDRF / IAF / BRO / POLICE
            sector TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            strength INTEGER DEFAULT 0,
            vehicles TEXT DEFAULT '[]',  -- JSON list of vehicles
            status TEXT NOT NULL DEFAULT 'STANDBY',
            contact TEXT,
            last_updated TEXT NOT NULL
        )
    """)

    # ─── 2. RIVER BASINS TABLE ────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS river_basins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            river TEXT NOT NULL,
            gauge_station TEXT,
            current_level REAL NOT NULL,
            danger_level REAL NOT NULL,
            warning_level REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'SAFE',
            trend TEXT DEFAULT 'Steady',
            lat REAL,
            lng REAL,
            last_updated TEXT NOT NULL
        )
    """)

    # ─── 3. CITIZEN SOS SIGNALS TABLE ────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS sos_signals (
            id TEXT PRIMARY KEY,
            caller_name TEXT NOT NULL,
            phone TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            location_name TEXT,
            details TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            assigned_unit TEXT DEFAULT 'Unassigned',
            nearest_unit_id TEXT,
            eta_minutes INTEGER,
            distance_km REAL,
            priority TEXT DEFAULT 'HIGH',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # ─── 4. INCIDENTS / ALERTS TABLE ─────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            msg TEXT NOT NULL,
            zone TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'MEDIUM',
            lat REAL,
            lng REAL,
            risk_score INTEGER DEFAULT 0,
            is_simulated INTEGER DEFAULT 0,
            ai_analysis TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # ─── 5. SIMULATION SESSIONS TABLE ────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS simulation_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_name TEXT NOT NULL,
            rainfall REAL NOT NULL,
            slope REAL NOT NULL,
            elevation REAL NOT NULL,
            soil TEXT,
            cloudburst INTEGER DEFAULT 0,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            pop_at_risk INTEGER DEFAULT 0,
            runoff_velocity REAL,
            lead_time_minutes INTEGER,
            explanation TEXT,
            ai_analysis TEXT,
            operator_id TEXT DEFAULT 'SEOC-AUTO',
            created_at TEXT NOT NULL
        )
    """)

    # ─── 6. DISPATCH ORDERS TABLE ─────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS dispatch_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_ref TEXT UNIQUE NOT NULL,
            sos_id TEXT,
            unit_id TEXT,
            target_sector TEXT NOT NULL,
            objective TEXT,
            status TEXT DEFAULT 'TRANSMITTED',
            authorized_by TEXT DEFAULT 'SEOC-DUTY-OFFICER',
            created_at TEXT NOT NULL
        )
    """)

    # ─── 7. AI BROADCASTS LOG ─────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_city TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            msg_english TEXT,
            msg_hindi TEXT,
            msg_garhwali TEXT,
            msg_kumaoni TEXT,
            channels TEXT DEFAULT '["Cell SMS", "Temple PA", "AIR FM"]',
            ai_generated INTEGER DEFAULT 0,
            operator_id TEXT DEFAULT 'SEOC-AUTO',
            created_at TEXT NOT NULL
        )
    """)

    # ─── 8. WEATHER CACHE TABLE ───────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS weather_cache (
            city_name TEXT PRIMARY KEY,
            lat REAL,
            lng REAL,
            temperature REAL,
            precipitation REAL,
            wind_speed REAL,
            humidity REAL,
            raw_json TEXT,
            fetched_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    # ─── 9. LORA MESH RELAY NODES (865-867 MHz INDIA ISM BAND) ────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS lora_nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            role TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            elevation_m REAL NOT NULL,
            frequency_mhz REAL DEFAULT 865.2,
            spreading_factor INTEGER DEFAULT 7,
            tx_power_dbm INTEGER DEFAULT 14,
            rssi_dbm INTEGER DEFAULT -88,
            snr_db REAL DEFAULT 7.5,
            battery_pct INTEGER DEFAULT 95,
            status TEXT DEFAULT 'ACTIVE',
            uplink_type TEXT DEFAULT 'RF_MESH',
            last_seen TEXT NOT NULL
        )
    """)

    # ─── 10. LORA PACKET INSPECTOR STREAM ─────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS lora_packets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            packet_hash TEXT UNIQUE NOT NULL,
            source_node TEXT NOT NULL,
            destination_node TEXT DEFAULT 'LORA-GW-05',
            hop_count INTEGER DEFAULT 1,
            max_hops INTEGER DEFAULT 5,
            packet_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            raw_hex TEXT NOT NULL,
            rssi_dbm INTEGER DEFAULT -92,
            snr_db REAL DEFAULT 6.8,
            created_at TEXT NOT NULL
        )
    """)

    # ─── 11. COMMUNITY FIRST RESPONDERS & SHELTERS (P2P MUTUAL AID) ───────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS community_assists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            volunteer_name TEXT NOT NULL,
            phone TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            location_name TEXT,
            action_type TEXT NOT NULL,  -- OFFERING_SHELTER / OFFERING_FOOD / EN_ROUTE_TO_HELP / FIRST_AID
            details TEXT NOT NULL,
            capacity INTEGER DEFAULT 5,
            target_sos_id TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    _seed_initial_data(conn)
    conn.close()
    print("[DB] Rakshak SQLite database initialized at:", DB_PATH)


def _seed_initial_data(conn: sqlite3.Connection):
    """Seed initial field units and river basin data if tables are empty."""
    c = conn.cursor()
    now = datetime.utcnow().isoformat()

    # Seed field units only if empty
    c.execute("SELECT COUNT(*) FROM field_units")
    if c.fetchone()[0] == 0:
        units = [
            ("NDRF-8", "NDRF 8th Battalion", "Vajra-1", "NDRF", "Gauchar Base", 30.2980, 79.1620, 36, '["4 River Inflatables","Satellite Phone","Medical Kit","Rope Rescue"]', "PRE-POSITIONED", "+91-135-2710334"),
            ("SDRF-M1", "SDRF High Altitude Rescue", "Cheetah-Alpha", "SDRF", "Guptkashi", 30.5840, 79.0520, 18, '["2 Rescue Jeeps","Rope Harness Set","Drone Search Unit"]', "PATROL EN ROUTE", "+91-135-2410882"),
            ("IAF-CH1", "IAF Chetak Air-Ambulance", "Garuda-3", "IAF", "Sahastradhara Helipad", 30.3420, 78.0860, 4, '["Chetak Helicopter","Winch Rescue","Emergency Medical Bay"]', "STANDBY", "Air Control 121.5 MHz"),
            ("BRO-TF7", "BRO Task Force Shivalik", "Mountain-Clear", "BRO", "Joshimath KM-48", 30.5600, 79.5800, 24, '["2 Heavy Bulldozers","Rock Breakers","Road Repair Vehicle"]', "CLEARING DEBRIS", "VHF Ch-08"),
            ("SDRF-P1", "SDRF Pithoragarh", "Kali-1", "SDRF", "Pithoragarh Base", 29.5829, 80.2182, 12, '["1 Rescue Jeep","Rope Set"]', "STANDBY", "+91-5964-224226"),
        ]
        c.executemany("""
            INSERT INTO field_units (id, name, callsign, unit_type, sector, lat, lng, strength, vehicles, status, contact, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8], u[9], u[10], now) for u in units])
        print("[DB] Seeded 5 field units.")

    # Seed river basins only if empty
    c.execute("SELECT COUNT(*) FROM river_basins")
    if c.fetchone()[0] == 0:
        basins = [
            ("Mandakini at Rudraprayag", "Rudraprayag Gauge Station CWC", 624.8, 627.0, 625.5, "WARNING", "+0.4m/hr", 30.2844, 78.9811),
            ("Alaknanda at Joshimath", "Joshimath Gauge Station", 1148.2, 1152.5, 1150.0, "NOMINAL", "+0.1m/hr", 30.5506, 79.5660),
            ("Bhagirathi at Uttarkashi", "Uttarkashi CWC Station", 1120.0, 1125.0, 1122.0, "NOMINAL", "Steady", 30.7268, 78.4354),
            ("Tehri Dam Reservoir", "THDC Tehri Control Room", 818.5, 830.0, 825.0, "SAFE", "+0.2m/day", 30.3804, 78.4800),
            ("Kali at Dharchula", "SSB Dharchula Station", 940.2, 943.0, 941.5, "NOMINAL", "Steady", 29.8519, 80.5284),
        ]
        c.executemany("""
            INSERT INTO river_basins (river, gauge_station, current_level, danger_level, warning_level, status, trend, lat, lng, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], now) for b in basins])
        print("[DB] Seeded 5 river basin records.")

    # Seed initial incident alerts
    c.execute("SELECT COUNT(*) FROM incidents")
    if c.fetchone()[0] == 0:
        alerts = [
            ("WARNING", "IMD Doppler Radar: Sustained rain cells detected over Chamoli & Rudraprayag corridors. Cumulus towers developing.", "Rudraprayag Sector", "HIGH", 30.2844, 78.9811, 45),
            ("ADVISORY", "BRO Task Force Shivalik reports boulder debris cleared at NH-07 KM 48. Single-lane traffic restored.", "Joshimath Axis", "MEDIUM", 30.5506, 79.5660, 30),
            ("LOGISTICS", "SDRF forward shelters at Sonprayag & Govindghat stocked: 4,000 emergency ration packets distributed.", "Kedarnath Basin", "INFO", 30.6375, 78.9950, 20),
        ]
        c.executemany("""
            INSERT INTO incidents (type, msg, zone, priority, lat, lng, risk_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [(a[0], a[1], a[2], a[3], a[4], a[5], a[6], now) for a in alerts])

        # Seed initial SOS signals
        sos = [
            ("SOS-701", "Pooja Dobhal & Family (4)", "+91 98450 11204", 30.6558, 79.0289, "Gaurikund Trek KM 3.2", "Landslide mud blocking downhill trail. 4 pilgrims sheltered in tin shed, low drinking water.", "DISPATCHED", "SDRF High Altitude Rescue", "SDRF-M1", 35, 8.4),
            ("SOS-702", "Driver Surender Singh (Bolero Taxi)", "+91 94120 88319", 30.5506, 79.5660, "Joshimath Upper Bypass", "Tree fallen across road, vehicle axle cracked. 6 passengers safe inside vehicle.", "PENDING", "Unassigned", None, None, None),
            ("SOS-703", "Gram Pradhan Rampur", "+91 97561 02931", 30.5230, 79.0833, "Guptkashi Rampur Outskirts", "Local stream overflowed into 2 cattle sheds. Elderly evacuation assistance needed.", "EN ROUTE", "District Rapid Force Unit 2", None, 52, 12.1),
        ]
        c.executemany("""
            INSERT INTO sos_signals (id, caller_name, phone, lat, lng, location_name, details, status, assigned_unit, nearest_unit_id, eta_minutes, distance_km, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10], s[11], now, now) for s in sos])
        print("[DB] Seeded initial alerts and SOS signals.")

    # Seed initial weather cache
    c.execute("SELECT COUNT(*) FROM weather_cache")
    if c.fetchone()[0] == 0:
        weather_seeds = [
            ("Rudraprayag", 30.2844, 78.9811, 24.5, 14.0, 8.2, 72.0),
            ("Chamoli", 30.4000, 79.3300, 21.0, 28.5, 11.4, 78.0),
            ("Joshimath", 30.5506, 79.5660, 16.5, 36.0, 15.0, 81.0),
            ("Dehradun", 30.3165, 78.0322, 28.0, 8.0, 6.5, 62.0),
            ("Kedarnath", 30.7352, 79.0669, 11.2, 42.0, 18.5, 88.0),
        ]
        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        c.executemany("""
            INSERT INTO weather_cache (city_name, lat, lng, temperature, precipitation, wind_speed, humidity, raw_json, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)
        """, [(w[0], w[1], w[2], w[3], w[4], w[5], w[6], now, expires) for w in weather_seeds])
        print("[DB] Seeded baseline weather cache.")

    # Seed Himalayan LoRa Mesh Nodes (Mandakini & Alaknanda Gorges)
    c.execute("SELECT COUNT(*) FROM lora_nodes")
    if c.fetchone()[0] == 0:
        nodes = [
            ("LORA-ND-01", "Kedarnath Ridge Optical Node", "Kedarnath Upper", "SENSOR_NODE", 30.7352, 79.0669, 3583, 865.2, 9, 14, -89, 7.8, 94, "ACTIVE", "RF_MESH"),
            ("LORA-ND-02", "Lincheli Forward Repeater", "Lincheli Gorge", "REPEATER", 30.6720, 79.0480, 3100, 865.4, 8, 14, -84, 8.2, 91, "ACTIVE", "RF_MESH"),
            ("LORA-ND-03", "Rambara Surge Bridge Relay", "Rambara Corridor", "REPEATER", 30.6975, 79.0435, 2800, 865.2, 10, 14, -104, 5.4, 82, "RELAYING", "RF_MESH"),
            ("LORA-ND-04", "Gaurikund Chatti Gate Node", "Gaurikund Axis", "SENSOR_NODE", 30.6558, 79.0289, 1982, 865.6, 7, 14, -82, 9.1, 88, "ACTIVE", "RF_MESH"),
            ("LORA-GW-05", "Sonprayag Valley Master Gateway", "Sonprayag Base", "GATEWAY", 30.6375, 78.9950, 1829, 865.0, 7, 20, -74, 11.2, 100, "ACTIVE", "FIBER_GATEWAY"),
            ("LORA-ND-06", "Guptkashi Ridge Transceiver", "Guptkashi Sector", "REPEATER", 30.5230, 79.0833, 1319, 866.0, 8, 14, -87, 8.0, 86, "ACTIVE", "RF_MESH"),
            ("LORA-ND-07", "Joshimath Dhauliganga Watch", "Joshimath KM-48", "SENSOR_NODE", 30.5506, 79.5660, 1890, 865.8, 9, 14, -93, 6.9, 93, "ACTIVE", "RF_MESH"),
            ("LORA-GW-08", "Rudraprayag SEOC Central Bridge", "Rudraprayag Sangam", "GATEWAY", 30.2844, 78.9811, 895, 865.0, 7, 20, -71, 12.0, 100, "ACTIVE", "SATELLITE_IP"),
        ]
        c.executemany("""
            INSERT INTO lora_nodes (id, name, sector, role, lat, lng, elevation_m, frequency_mhz, spreading_factor, tx_power_dbm, rssi_dbm, snr_db, battery_pct, status, uplink_type, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(n[0], n[1], n[2], n[3], n[4], n[5], n[6], n[7], n[8], n[9], n[10], n[11], n[12], n[13], n[14], now) for n in nodes])
        print("[DB] Seeded 8 Himalayan LoRa mesh nodes.")

    # Seed sample decoded LoRa RF packets
    c.execute("SELECT COUNT(*) FROM lora_packets")
    if c.fetchone()[0] == 0:
        packets = [
            ("PKT-9A4F12", "LORA-ND-01", "LORA-GW-05", 3, 5, "SENSOR_TELEMETRY", '{"water_level_m": 4.12, "soil_moisture_pct": 82, "rainfall_rate_mmhr": 48.5, "temp_c": 9.4}', "4C4F5241019A4F1204125200300940", -94, 6.5),
            ("PKT-8B2E09", "LORA-ND-03", "LORA-GW-05", 2, 5, "SENSOR_TELEMETRY", '{"water_level_m": 6.85, "river_velocity_mps": 5.4, "warning_level": true}', "4C4F5241038B2E090685054001", -102, 5.1),
            ("PKT-7C1D88", "LORA-ND-04", "LORA-GW-05", 1, 5, "BEACON", '{"mesh_neighbors": ["LORA-ND-03", "LORA-GW-05"], "battery_v": 3.95}', "4C4F5241047C1D88020305", -82, 9.4),
            ("PKT-5D9E44", "LORA-ND-01", "LORA-GW-05", 4, 5, "SOS_DISTRESS", '{"caller": "Gaurikund Pilgrim Group", "lat": 30.6558, "lng": 79.0289, "details": "Mudslide blocked trail near bridge. 6 sheltered in tea shack."}', "4C4F5241534F53010461", -91, 7.2),
        ]
        c.executemany("""
            INSERT INTO lora_packets (packet_hash, source_node, destination_node, hop_count, max_hops, packet_type, payload_json, raw_hex, rssi_dbm, snr_db, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], now) for p in packets])
        print("[DB] Seeded initial LoRa RF packet stream.")

    # Seed Community First Responders & Safe Havens (P2P Mutual Aid)
    c.execute("SELECT COUNT(*) FROM community_assists")
    if c.fetchone()[0] == 0:
        assists = [
            ("Rameshwar Semwal (Shiv Shakti Dhaba)", "+91 98371 44520", 30.6975, 79.0435, "Rambara Gorge Upper", "OFFERING_SHELTER", "Concrete 2nd floor hall dry & safe. 25 dry blankets, boiled water & warm tea ready for stranded pilgrims.", 25, None),
            ("Swami Vishuddhanand (Gaurikund Temple Trust)", "+91 94115 88912", 30.6558, 79.0289, "Gaurikund Main Bazaar", "OFFERING_SHELTER", "Temple Dharmshala upper wing open. Hot food, solar battery charging, and first-aid kits available for up to 40 people.", 40, None),
            ("Devender Rawat (Sonprayag Taxi & Mule Union)", "+91 97580 33140", 30.6375, 78.9950, "Sonprayag Confluence", "EN_ROUTE_TO_HELP", "4 volunteer mountain drivers with 4x4 Boleros stationed at Sonprayag barrier. Ready for emergency elderly evacuation.", 15, "SOS-701"),
        ]
        c.executemany("""
            INSERT INTO community_assists (volunteer_name, phone, lat, lng, location_name, action_type, details, capacity, target_sos_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
        """, [(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], now) for a in assists])
        print("[DB] Seeded 3 community first responder shelters.")

    conn.commit()

