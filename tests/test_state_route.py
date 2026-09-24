import os
import sqlite3
import tempfile

import backend.core.database as dbmod
from backend.api.routes.state import get_state


def test_get_state_handles_null_strengths():
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    original_db_path = dbmod.DB_PATH
    dbmod.DB_PATH = temp_db
    try:
        dbmod.init_db()
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "DELETE FROM field_units"
        )
        conn.execute(
            "INSERT INTO field_units (id, name, callsign, unit_type, sector, lat, lng, strength, vehicles, status, contact, last_updated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("U1", "Alpha Unit", "Vajra-1", "SDRF", "Rudraprayag", 30.3, 79.1, None, '[]', "STANDBY", "+91", "2024-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.close()

        state = get_state()

        assert state["summary"]["totalFieldStrength"] == 0
        assert state["summary"]["deployedUnits"] == 0
        assert state["fieldUnits"][0]["strength"] == 0
    finally:
        dbmod.DB_PATH = original_db_path
        try:
            os.remove(temp_db)
        except FileNotFoundError:
            pass
