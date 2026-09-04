import json
import logging
from typing import Any, TypeVar

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Cache TTLs in seconds
VEHICLE_CACHE_TTL = 60 * 5  # 5 minutes
USER_IDENTITY_TTL = 60 * 5  # 5 minutes


class _CacheMissType:
    """Sentinel so cached JSON null is distinct from a Redis miss."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "CACHE_MISS"


CACHE_MISS = _CacheMissType()


# ── Key builders ──────────────────────────────────────────────

def user_identity_key(user_id: str) -> str:
    """Cache key for auth identity (no password)."""
    return f"cache:user:{user_id}"


def user_identity_payload(user: Any) -> dict[str, Any]:
    """Public fields stored in the identity cache. Never include hashed_password."""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": bool(user.is_active),
        "email_verified": bool(getattr(user, "email_verified", False)),
        "email_service_reminders": bool(
            getattr(user, "email_service_reminders", True)
        ),
        "email_document_reminders": bool(
            getattr(user, "email_document_reminders", True)
        ),
    }


def vehicle_list_key(user_id: str) -> str:
    """Cache key for a user's vehicle list."""
    return f"cache:vehicles:user:{user_id}"


def vehicle_detail_key(vehicle_id: str) -> str:
    """Cache key for a single vehicle."""
    return f"cache:vehicle:{vehicle_id}"


def vehicle_summary_key(vehicle_id: str) -> str:
    """Cache key for vehicle dashboard summary."""
    return f"cache:vehicle_summary:{vehicle_id}"


def vehicle_analytics_key(vehicle_id: str) -> str:
    """Cache key for vehicle analytics charts."""
    return f"cache:vehicle_analytics:{vehicle_id}"


def vehicle_compare_key(user_id: str) -> str:
    """Cache key for garage compare. Invalidated with cache:vehicles:user:{id}*."""
    return f"cache:vehicles:user:{user_id}:compare"


# ── Core get/set helpers ──────────────────────────────────────

def parse_cached_json(raw: bytes | str | None) -> Any | None:
    """Decode a Redis cache blob. None on miss or invalid JSON."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def parse_user_identity(raw: bytes | str | None) -> dict[str, Any] | None:
    """Decode a cached user identity dict. None on miss or invalid shape."""
    data = parse_cached_json(raw)
    if not isinstance(data, dict) or "id" not in data or "email" not in data:
        return None
    return data


async def cache_get(redis: Redis, key: str) -> Any | _CacheMissType:
    """
    Get a value from cache.
    Returns CACHE_MISS on miss or Redis errors.
    Cached JSON null is returned as None (a hit).
    Never raises — cache failures are non-fatal.
    """
    try:
        value = await redis.get(key)
        if value is None:
            return CACHE_MISS
        return json.loads(value)
    except Exception as e:
        logger.warning("Cache GET failed key=%s error=%s", key, e)
        return CACHE_MISS


async def cache_set(
    redis: Redis,
    key: str,
    value: Any,
    ttl: int,
) -> None:
    """
    Set a value in cache with TTL.
    Never raises — cache failures are non-fatal.
    """
    try:
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning("Cache SET failed key=%s error=%s", key, e)


async def cache_delete(redis: Redis, *keys: str) -> None:
    """
    Delete one or more cache keys.
    Used for cache invalidation on write operations.
    Never raises.
    """
    try:
        if keys:
            await redis.delete(*keys)
    except Exception as e:
        logger.warning("Cache DELETE failed keys=%s error=%s", keys, e)


async def cache_delete_pattern(redis: Redis, pattern: str) -> None:
    """
    Delete all keys matching a pattern.
    Used for broad invalidation (e.g. all vehicle caches for a user).
    Uses SCAN to avoid blocking Redis.
    """
    try:
        async for key in redis.scan_iter(pattern):
            await redis.delete(key)
    except Exception as e:
        logger.warning(
            "Cache DELETE pattern failed pattern=%s error=%s", pattern, e
        )
