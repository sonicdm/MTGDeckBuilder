"""
cache_helper.py: Universal cache logic for SQLAlchemy repositories (session + objects).

Usage:
    from .cache_helper import get_universal_cache
    session, objects = get_universal_cache(
        db_path, session_factory, loader_func, columns=columns, ttl=60
    )

- db_path: path to the database file (for mtime checks)
- session_factory: callable that returns a context manager yielding a session
- loader_func: function(session, columns) -> list of objects (e.g., CardDB)
- columns: list of columns to load (optional)
- ttl: cache time-to-live in seconds (default 60)
"""
import os
import time
from threading import Lock

# Global cache dict and lock
_universal_cache = {}
_cache_lock = Lock()

def get_universal_cache(db_path, session_factory, loader_func, columns=None, ttl=60):
    """
    Universal cache for (session, objects), keyed by (db_path, columns tuple).
    Returns (session, objects).
    """
    cache_key = (db_path, tuple(columns) if columns else None)
    mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else None
    now = time.time()
    with _cache_lock:
        cache = _universal_cache.get(cache_key)
        if cache and cache['mtime'] == mtime and now - cache['timestamp'] < ttl:
            return cache['session'], cache['objects']
        # Close old session if present
        if cache and cache['session'] is not None:
            try:
                close_method = getattr(cache['session'], 'close', None)
                if callable(close_method):
                    close_method()
            except Exception:
                pass
        # Create new session and load objects
        with session_factory() as session:
            objects = loader_func(session, columns)
        # Store session and objects in cache (keep session open)
        session = session_factory().__enter__()
        _universal_cache[cache_key] = {
            'session': session,
            'objects': objects,
            'mtime': mtime,
            'timestamp': now,
        }
        return session, objects

