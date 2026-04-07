"""Multi-key manager with sequential fallback and parallel execution.

Reads keys from user_api_keys table, tries in priority order,
tracks failures, and supports parallel distribution for embedding.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AllKeysExhausted(Exception):
    """All API keys for a provider have been exhausted or failed."""
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"All {provider} keys exhausted")


class KeyManager:
    """Manages multiple API keys per provider with fallback and parallel support."""

    def __init__(self, sb, user_id: str):
        self.sb = sb
        self.user_id = user_id
        self._cache: dict[str, list[dict]] = {}

    def get_keys(self, provider: str) -> list[dict]:
        """Return active keys for provider, ordered by priority (0=first).

        Returns list of dicts: [{id, api_key_encrypted, priority, label}]
        """
        if provider in self._cache:
            return self._cache[provider]
        try:
            result = (
                self.sb.table("user_api_keys")
                .select("id, api_key_encrypted, priority, label")
                .eq("user_id", self.user_id)
                .eq("provider", provider)
                .eq("is_active", True)
                .order("priority")
                .execute()
            )
            keys = result.data or []
            self._cache[provider] = keys
            return keys
        except Exception as exc:
            logger.warning("key_manager: failed to fetch keys for %s: %s", provider, exc)
            return []

    def get_single_key(self, provider: str) -> Optional[str]:
        """Return highest-priority active key for provider, or None."""
        keys = self.get_keys(provider)
        return keys[0]["api_key_encrypted"] if keys else None

    async def call_with_fallback(
        self,
        provider: str,
        call_fn: Callable[[str], Any],
        fallback_key: Optional[str] = None,
    ) -> Any:
        """Try each key in priority order. Falls back to fallback_key if all fail.

        call_fn receives the raw API key string and should return the result.
        Raises AllKeysExhausted if all keys fail and no fallback provided.
        """
        keys = self.get_keys(provider)

        for key_row in keys:
            api_key = key_row["api_key_encrypted"]
            key_id = key_row["id"]
            try:
                result = await call_fn(api_key)
                self._mark_used(key_id)
                return result
            except Exception as exc:
                status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
                if status_code == 429:
                    logger.warning("key_manager: %s key %s rate-limited, trying next", provider, key_row["label"])
                    self._mark_failure(key_id)
                    continue
                # Non-rate-limit error — still try next key
                logger.warning("key_manager: %s key %s failed (%s), trying next", provider, key_row["label"], exc)
                self._mark_failure(key_id)
                continue

        # All DB keys exhausted — try fallback
        if fallback_key:
            logger.info("key_manager: all %s DB keys exhausted, using fallback", provider)
            return await call_fn(fallback_key)

        raise AllKeysExhausted(provider)

    async def call_parallel(
        self,
        provider: str,
        items: list,
        call_fn: Callable[[str, list], Any],
    ) -> list:
        """Distribute items across all active keys in parallel.

        call_fn receives (api_key, items_chunk) and returns a list of results.
        Results are flattened and returned in order.

        Ideal for embedding: 2 Jina keys = 2x throughput.
        """
        keys = self.get_keys(provider)
        if not keys:
            raise AllKeysExhausted(provider)

        # Distribute items evenly across keys
        n_keys = len(keys)
        chunks = [items[i::n_keys] for i in range(n_keys)]

        tasks = []
        for key_row, chunk in zip(keys, chunks):
            if chunk:  # skip empty chunks
                tasks.append(call_fn(key_row["api_key_encrypted"], chunk))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results, skip exceptions
        flat = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("key_manager: parallel call failed: %s", r)
                continue
            if isinstance(r, list):
                flat.extend(r)
            else:
                flat.append(r)
        return flat

    def _mark_used(self, key_id: str) -> None:
        """Update last_used_at timestamp."""
        try:
            self.sb.table("user_api_keys").update(
                {"last_used_at": "now()"}
            ).eq("id", key_id).execute()
        except Exception:
            pass

    def _mark_failure(self, key_id: str) -> None:
        """Increment fail_count and set last_failed_at."""
        try:
            # Use RPC or raw SQL for atomic increment — fallback to read+write
            row = self.sb.table("user_api_keys").select("fail_count").eq("id", key_id).execute()
            current = (row.data[0]["fail_count"] if row.data else 0) or 0
            self.sb.table("user_api_keys").update({
                "fail_count": current + 1,
                "last_failed_at": "now()",
            }).eq("id", key_id).execute()
        except Exception:
            pass
