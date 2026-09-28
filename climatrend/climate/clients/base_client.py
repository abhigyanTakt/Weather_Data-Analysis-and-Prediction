"""
Base Resilient HTTP Client.
Implements exponential backoff retries, connection/read timeouts,
in-memory and disk caching with TTL, and seamless fallback data handling.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

import requests
from cachetools import TTLCache

from climatrend.climate.config import (
    CLIMATE_CACHE_DIR,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_CACHE_TTL_HOURLY,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_READ_TIMEOUT,
)

logger = logging.getLogger(__name__)


class BaseResilientClient:
    """
    Robust HTTP client with multi-layer resilience:
    1. Fast in-memory TTLCache
    2. Persistent disk cache fallback
    3. Exponential backoff retries on transient errors (5xx, timeouts, connection drop)
    4. Graceful default fallback return if all retries fail
    """

    def __init__(
        self,
        name: str = "base_client",
        cache_ttl: int = DEFAULT_CACHE_TTL_HOURLY,
        max_cache_entries: int = 500,
        max_retries: int = DEFAULT_MAX_RETRIES,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
    ):
        self.name = name
        self.max_retries = max_retries
        self.timeouts: Tuple[float, float] = (connect_timeout, read_timeout)
        self.cache: TTLCache = TTLCache(maxsize=max_cache_entries, ttl=cache_ttl)
        self.disk_cache_dir: Path = CLIMATE_CACHE_DIR / name
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        raw = f"{url}?{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _load_disk_cache(self, key: str) -> Optional[Any]:
        cache_file = self.disk_cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("payload")
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to read disk cache {cache_file}: {e}")
        return None

    def _save_disk_cache(self, key: str, payload: Any) -> None:
        cache_file = self.disk_cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"timestamp": time.time(), "payload": payload}, f)
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to write disk cache {cache_file}: {e}")

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        fallback: Optional[Union[Dict[str, Any], list, Callable[[], Any]]] = None,
        use_cache: bool = True,
    ) -> Any:
        """
        Performs a resilient GET request returning JSON.
        If the request fails after all retries, returns cached disk data or the provided fallback.
        """
        cache_key = self._get_cache_key(url, params)

        # 1. Check in-memory cache
        if use_cache and cache_key in self.cache:
            logger.debug(f"[{self.name}] Cache hit (in-memory) for {url}")
            return self.cache[cache_key]

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"[{self.name}] GET {url} (Attempt {attempt}/{self.max_retries})")
                response = self.session.get(
                    url, params=params, headers=headers, timeout=self.timeouts
                )
                
                # Check for rate limits or server errors
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2))
                    logger.warning(f"[{self.name}] Rate limit (429). Backing off for {retry_after}s.")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()

                # Store in memory & disk cache
                if use_cache:
                    self.cache[cache_key] = data
                    self._save_disk_cache(cache_key, data)

                return data

            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
                last_error = e
                backoff_time = DEFAULT_BACKOFF_FACTOR ** attempt
                logger.warning(
                    f"[{self.name}] Request error on attempt {attempt}: {str(e)}. "
                    f"Retrying in {backoff_time:.1f}s..."
                )
                if attempt < self.max_retries:
                    time.sleep(backoff_time)
            except Exception as e:
                last_error = e
                logger.error(f"[{self.name}] Unexpected error calling {url}: {str(e)}")
                break

        # 2. Check disk cache as backup
        disk_data = self._load_disk_cache(cache_key)
        if disk_data is not None:
            logger.warning(f"[{self.name}] Network failed; using stale disk cache for {url}")
            return disk_data

        # 3. Fallback to provided default
        logger.warning(f"[{self.name}] Request exhausted; triggering fallback for {url}. Error: {last_error}")
        if callable(fallback):
            return fallback()
        return fallback if fallback is not None else {}
