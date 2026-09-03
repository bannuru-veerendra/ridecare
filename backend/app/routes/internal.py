"""Internal cron / ops endpoints (secured by shared secret, not user JWT)."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.utils.redis_client import get_redis
from app.utils.reminder_digest import send_reminder_digests

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_cron_secret(
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> None:
    expected = (settings.REMINDER_CRON_SECRET or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reminder digests are not configured",
        )
    if not x_cron_secret or x_cron_secret != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cron secret",
        )


@router.post("/reminder-digests")
async def trigger_reminder_digests(
    _: None = Depends(_require_cron_secret),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict:
    """
    Send daily reminder emails for soon/overdue service and document expiry.

    Call from Render Cron (or similar) with header X-Cron-Secret.
    """
    result = await send_reminder_digests(db, redis)
    return {
        "users_considered": result.users_considered,
        "emails_sent": result.emails_sent,
        "emails_skipped": result.emails_skipped,
    }
