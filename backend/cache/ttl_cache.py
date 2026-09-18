"""
Project Rakshak — TTL Cache
Thread-safe, in-memory time-to-live cache for API responses.
"""

import threading
import time
from typing import Any, Optional, Dict, Tuple


class TTLCache:
    """
    Simple in-memory key/value store with per-entry TTL expiry.
    Thread-safe via a reentrant lock.
    """

    def __init__(self):
        self._store: Dict[str, Tuple[Any, float]] = {}  # key → (value, expires_at)
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        with self._lock:
            self._store[key] = (value, time.time() + ttl_seconds)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            active = {k: v for k, (v, exp) in self._store.items() if now <= exp}
            return {"total_entries": len(self._store), "active_entries": len(active)}


# ─── Singleton instances ───────────────────────────────────────────────────────
weather_cache = TTLCache()   # 15-minute TTL for Open-Meteo responses
gemini_cache = TTLCache()    # 5-minute TTL for Gemini AI-generated alerts
state_cache = TTLCache()     # 30-second TTL for live system state snapshot

