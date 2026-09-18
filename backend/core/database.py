"""
Project Rakshak - Uttarakhand SEOC
SQLite Database Schema, Initialization, and Connection Manager
"""

import sqlite3
import os
from datetime import datetime
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
        from datetime import timedelta
        expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        c.executemany("""
            INSERT INTO weather_cache (city_name, lat, lng, temperature, precipitation, wind_speed, humidity, raw_json, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '{}', ?, ?)
        """, [(w[0], w[1], w[2], w[3], w[4], w[5], w[6], now, expires) for w in weather_seeds])
        print("[DB] Seeded baseline weather cache.")

    conn.commit()

