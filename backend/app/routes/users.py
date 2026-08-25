import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import PasswordUpdate, UserProfileUpdate, UserResponse
from app.utils.access_token_service import revoke_all_user_access_tokens
from app.utils.auth_cookies import clear_auth_cookies
from app.utils.auth_dependency import get_current_user
from app.utils.cache import (
    USER_IDENTITY_TTL,
    cache_delete,
    cache_set,
    user_identity_key,
    user_identity_payload,
)
from app.utils.email import send_verification_email
from app.utils.email_verification_service import (
    store_verification_token,
    verification_link,
)
from app.utils.redis_client import get_redis
from app.utils.refresh_token_service import revoke_all_user_tokens
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

_REDIS_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Authentication service temporarily unavailable",
)


async def _user_for_write(db: AsyncSession, current_user: User) -> User:
    """Session-attached User. Cached auth identity is not writable."""
    db_user = await db.get(User, current_user.id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return db_user


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get the current authenticated user's profile"""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    profile_update: UserProfileUpdate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserResponse:
    """Update the current user's name or email"""
    db_user = await _user_for_write(db, current_user)
    updates = profile_update.model_dump(exclude_unset=True)
    email_changed = False

    if "email" in updates and updates["email"] != db_user.email:
        existing_user = await db.execute(
            select(User).where(
                User.email == updates["email"],
                User.id != db_user.id,
            )
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        db_user.email = updates["email"]
        db_user.email_verified = False
        email_changed = True
        del updates["email"]

        try:
            raw_token = await store_verification_token(redis, str(db_user.id))
            await send_verification_email(
                to=db_user.email,
                full_name=(
                    updates.get("full_name")
                    if updates.get("full_name") is not None
                    else db_user.full_name
                ),
                link=verification_link(raw_token),
            )
        except RedisError:
            logger.exception(
                "Redis unavailable while issuing verification after email change"
            )
            await db.rollback()
            raise _REDIS_UNAVAILABLE
        except Exception:
            logger.exception(
                "Failed to send verification email after email change user=%s",
                db_user.id,
            )

    for key, value in updates.items():
        setattr(db_user, key, value)

    if email_changed:
        try:
            await revoke_all_user_tokens(redis, str(db_user.id))
            await revoke_all_user_access_tokens(redis, str(db_user.id))
            await cache_delete(redis, user_identity_key(str(db_user.id)))
        except RedisError:
            logger.exception(
                "Redis unavailable while revoking sessions after email change"
            )
            await db.rollback()
            raise _REDIS_UNAVAILABLE

    await db.commit()
    await db.refresh(db_user)

    if email_changed:
        clear_auth_cookies(response)
    else:
        await cache_set(
            redis,
            user_identity_key(str(db_user.id)),
            user_identity_payload(db_user),
            USER_IDENTITY_TTL,
        )

    logger.info(
        "User %s updated profile fields: %s",
        db_user.id,
        list(profile_update.model_dump(exclude_unset=True).keys()),
    )
    return db_user


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_update: PasswordUpdate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    """Change the current user's password and revoke all sessions"""
    db_user = await _user_for_write(db, current_user)
    if not verify_password(
        password_update.current_password,
        db_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    db_user.hashed_password = hash_password(password_update.new_password)

    try:
        await revoke_all_user_tokens(redis, str(db_user.id))
        await revoke_all_user_access_tokens(redis, str(db_user.id))
        await cache_delete(redis, user_identity_key(str(db_user.id)))
    except RedisError:
        logger.exception(
            "Redis unavailable while revoking sessions for user %s",
            db_user.id,
        )
        await db.rollback()
        raise _REDIS_UNAVAILABLE

    await db.commit()
    clear_auth_cookies(response)

    logger.info(
        "User %s changed password — all sessions revoked",
        db_user.id,
    )
