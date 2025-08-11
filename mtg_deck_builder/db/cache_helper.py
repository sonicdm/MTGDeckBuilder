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
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

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


class QueryCache:
    """Simple in-memory cache for database queries."""

    def __init__(self, max_size: int = 1000):
        """Initialize cache with maximum size."""
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_count: Dict[str, int] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.cache:
            self.access_count[key] += 1
            return self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        if len(self.cache) >= self.max_size:
            # Remove least accessed item
            least_accessed = min(
                self.access_count.items(), key=lambda x: x[1]
            )[0]
            del self.cache[least_accessed]
            del self.access_count[least_accessed]
        
        self.cache[key] = value
        self.access_count[key] = 1

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self.access_count.clear()


def cached_query(cache: QueryCache, key_func: Optional[Callable] = None):
    """Decorator to cache database query results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            logger.debug(f"Cache miss for {cache_key}")
            return result
        
        return wrapper
    return decorator

