import logging
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    ResendVerificationRequest,
    SessionResponse,
    TokenResponse,
    UserCreate,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse
from app.utils.access_token_service import blocklist_access_token
from app.utils.auth_cookies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    clear_auth_cookies,
    set_auth_cookies,
)
from app.utils.email import send_verification_email
from app.utils.email_verification_service import (
    consume_verification_token,
    store_verification_token,
    verification_link,
)
from app.utils.jwt import create_access_token
from app.utils.rate_limiter import auth_rate_limit
from app.utils.redis_client import get_redis
from app.utils.refresh_token_service import (
    revoke_refresh_token,
    rotate_refresh_token,
    store_refresh_token,
)
from app.utils.security import hash_password, normalize_email, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_REDIS_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Authentication service temporarily unavailable",
)

_EMAIL_NOT_VERIFIED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Email not verified. Check your inbox or request a new verification link.",
)


@dataclass(frozen=True, slots=True)
class _IssuedTokens:
    access_token: str
    refresh_token: str


async def _issue_verification_email(
    redis: Redis,
    *,
    user_id: str,
    email: str,
    full_name: str,
) -> None:
    """Create a Redis token and send the verification email."""
    try:
        raw_token = await store_verification_token(redis, user_id)
    except RedisError:
        logger.exception("Redis unavailable while storing verification token")
        raise _REDIS_UNAVAILABLE

    link = verification_link(raw_token)
    try:
        await send_verification_email(to=email, full_name=full_name, link=link)
    except Exception:
        logger.exception("Failed to send verification email to=%s", email)
        # User is created; they can use resend. Do not fail registration.


async def _authenticate_user(
    email: str,
    password: str,
    db: AsyncSession,
    redis: Redis,
) -> _IssuedTokens:
    """Validate credentials and issue access + refresh tokens."""
    email = normalize_email(email)
    result = await db.execute(select(User).where(User.email == email))
    db_user = result.scalar_one_or_none()

    if not db_user:
        logger.warning("Login failed: no user found for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not db_user.is_active:
        logger.warning("Login failed: inactive account for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(password, db_user.hashed_password):
        logger.warning("Login failed: wrong password for email=%s", email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not db_user.email_verified:
        logger.warning("Login failed: email not verified for email=%s", email)
        raise _EMAIL_NOT_VERIFIED

    user_id = str(db_user.id)
    access_token = create_access_token(user_id)
    try:
        refresh_token = await store_refresh_token(redis, user_id)
    except RedisError:
        logger.exception("Redis unavailable while issuing refresh token")
        raise _REDIS_UNAVAILABLE

    return _IssuedTokens(access_token=access_token, refresh_token=refresh_token)


def _refresh_token_from(request: Request, body: RefreshRequest | LogoutRequest) -> str | None:
    return body.refresh_token or request.cookies.get(REFRESH_COOKIE)


def _access_token_from(request: Request) -> str | None:
    """Prefer Bearer header, fall back to access cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer = auth_header.removeprefix("Bearer ").strip()
        if bearer:
            return bearer
    return request.cookies.get(ACCESS_COOKIE)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserResponse:
    """Register a new user and send an email verification link."""
    await auth_rate_limit(request, redis)

    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hash_password(user.password),
        email_verified=False,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    await _issue_verification_email(
        redis,
        user_id=str(db_user.id),
        email=db_user.email,
        full_name=db_user.full_name,
    )
    return db_user


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Consume a verification token and mark the user's email as verified."""
    await auth_rate_limit(request, redis)

    try:
        user_id = await consume_verification_token(redis, body.token)
    except RedisError:
        logger.exception("Redis unavailable during email verification")
        raise _REDIS_UNAVAILABLE

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if db_user is None or not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link",
        )

    if not db_user.email_verified:
        db_user.email_verified = True
        await db.commit()

    return MessageResponse(message="Email verified. You can sign in now.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: Request,
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Resend verification email.
    Always returns the same message to avoid email enumeration.
    """
    await auth_rate_limit(request, redis)

    result = await db.execute(select(User).where(User.email == body.email))
    db_user = result.scalar_one_or_none()
    if (
        db_user is not None
        and db_user.is_active
        and not db_user.email_verified
    ):
        await _issue_verification_email(
            redis,
            user_id=str(db_user.id),
            email=db_user.email,
            full_name=db_user.full_name,
        )

    return MessageResponse(
        message="If that email is registered and unverified, a new link has been sent.",
    )


@router.post("/login", response_model=SessionResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SessionResponse:
    """Login with JSON body (`email` + `password`). Sets httpOnly auth cookies."""
    await auth_rate_limit(request, redis)
    tokens = await _authenticate_user(
        credentials.email, credentials.password, db, redis
    )
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return SessionResponse()


@router.post("/token", response_model=TokenResponse)
async def token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """OAuth2 token endpoint for Swagger Authorize (`username` = email)."""
    await auth_rate_limit(request, redis)
    tokens = await _authenticate_user(
        form_data.username, form_data.password, db, redis
    )
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    redis: Redis = Depends(get_redis),
) -> SessionResponse:
    """Rotate refresh token and issue a new access token. Reads cookie if body omits token."""
    refresh_token = _refresh_token_from(request, body)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    try:
        result = await rotate_refresh_token(redis, refresh_token)
    except RedisError:
        logger.exception("Redis unavailable during refresh")
        raise _REDIS_UNAVAILABLE

    if result is None:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_refresh_token, user_id = result

    # Prefer to kill the previous access JWT immediately; if Redis blips here the
    # refresh already rotated — still issue new cookies (old access dies by TTL).
    old_access = _access_token_from(request)
    if old_access:
        try:
            await blocklist_access_token(redis, old_access)
        except RedisError:
            logger.exception(
                "Redis unavailable while blocklisting access token on refresh"
            )

    access_token = create_access_token(user_id)
    set_auth_cookies(response, access_token, new_refresh_token)
    return SessionResponse()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest = LogoutRequest(),
    redis: Redis = Depends(get_redis),
) -> Response:
    """Revoke refresh + blocklist access token, then clear auth cookies."""
    refresh_token = _refresh_token_from(request, body)
    access_token = _access_token_from(request)
    try:
        if refresh_token:
            await revoke_refresh_token(redis, refresh_token)
        if access_token:
            await blocklist_access_token(redis, access_token)
    except RedisError:
        logger.exception("Redis unavailable during logout")
        raise _REDIS_UNAVAILABLE
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
