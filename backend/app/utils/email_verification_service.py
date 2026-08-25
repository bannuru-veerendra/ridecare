"""Redis-backed one-time email verification tokens (mirrors refresh tokens)."""

import hashlib
import logging
import secrets

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

EMAIL_VERIFY_PREFIX = "email_verify:"
USER_EMAIL_VERIFY_PREFIX = "email_verify_user:"


def _make_key(token_hash: str) -> str:
    return f"{EMAIL_VERIFY_PREFIX}{token_hash}"


def _user_token_key(user_id: str) -> str:
    return f"{USER_EMAIL_VERIFY_PREFIX}{user_id}"


def _ttl_seconds() -> int:
    return settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS * 60 * 60


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _decode_redis_value(value: bytes | str) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return value


async def store_verification_token(redis: Redis, user_id: str) -> str:
    """
    Issue a verification token for the user.
    Replaces any previous outstanding token for that user.
    """
    user_key = _user_token_key(user_id)
    previous = await redis.get(user_key)
    if previous:
        await redis.delete(_make_key(_decode_redis_value(previous)))

    raw_token = generate_verification_token()
    token_hash = hash_verification_token(raw_token)
    ttl = _ttl_seconds()

    await redis.setex(_make_key(token_hash), ttl, user_id)
    await redis.setex(user_key, ttl, token_hash)
    return raw_token


async def consume_verification_token(redis: Redis, raw_token: str) -> str | None:
    """
    One-shot consume. Returns user_id if valid, else None.
    """
    token_hash = hash_verification_token(raw_token)
    user_id = await redis.getdel(_make_key(token_hash))
    if not user_id:
        logger.warning("Email verification token not found or already used")
        return None

    user_id = _decode_redis_value(user_id)
    await redis.delete(_user_token_key(user_id))
    return user_id


def verification_link(raw_token: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/verify-email?token={raw_token}"
