import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.access_token_service import (
    get_access_revoke_before,
    is_access_token_blocklisted,
)
from app.utils.cache import (
    USER_IDENTITY_TTL,
    cache_set,
    user_identity_key,
    user_identity_payload,
)
from app.utils.auth_context import get_access_token_from_request, get_auth_hot_path
from app.utils.jwt import decode_access_token
from app.utils.redis_client import get_redis

# auto_error=False so we can fall back to the httpOnly access cookie
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

_REDIS_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Authentication service temporarily unavailable",
)


def _parse_iat(payload: dict) -> int | None:
    iat = payload.get("iat")
    if hasattr(iat, "timestamp"):
        return int(iat.timestamp())
    if iat is None:
        return None
    try:
        return int(iat)
    except (TypeError, ValueError):
        return None


def _user_from_identity_cache(data: dict) -> User | None:
    """Build a read-only User from Redis. Do not flush this instance."""
    try:
        is_active = data.get("is_active", True)
        if not is_active:
            return None
        return User(
            id=uuid.UUID(str(data["id"])),
            email=data["email"],
            full_name=data["full_name"],
            hashed_password="",
            is_active=True,
            email_verified=bool(data.get("email_verified", False)),
        )
    except (KeyError, TypeError, ValueError):
        return None


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """Resolve the current user from Bearer token or access cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    hot = get_auth_hot_path(request)
    if hot is not None and hot.payload is not None:
        payload = hot.payload
    else:
        access = token or get_access_token_from_request(request)
        if not access:
            raise credentials_exception
        try:
            payload = decode_access_token(access)
        except (JWTError, ValueError):
            raise credentials_exception
        hot = None

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    jti = payload.get("jti")
    iat = _parse_iat(payload)

    try:
        if hot is not None:
            if hot.blocklisted:
                raise credentials_exception
            revoke_before = hot.revoke_before
        else:
            if jti and await is_access_token_blocklisted(redis, str(jti)):
                raise credentials_exception
            revoke_before = await get_access_revoke_before(redis, str(user_uuid))

        if revoke_before is not None:
            if iat is None or iat < revoke_before:
                raise credentials_exception
    except HTTPException:
        raise
    except RedisError:
        raise _REDIS_UNAVAILABLE

    if hot is not None and hot.cached_user is not None:
        if hot.cached_user.get("is_active") is False:
            raise credentials_exception
        cached = _user_from_identity_cache(hot.cached_user)
        if cached is not None and cached.id == user_uuid:
            return cached

    result = await db.execute(select(User).where(User.id == user_uuid))
    db_user = result.scalar_one_or_none()
    if db_user is None or not db_user.is_active:
        raise credentials_exception

    await cache_set(
        redis,
        user_identity_key(str(db_user.id)),
        user_identity_payload(db_user),
        USER_IDENTITY_TTL,
    )
    return db_user
