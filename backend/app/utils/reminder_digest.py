"""Daily email digests for service and document reminders."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy import func, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.document import Document
from app.models.fuel_log import FuelLog
from app.models.service_log import ServiceLog
from app.models.user import User
from app.models.vehicle import Vehicle
from app.utils.dates import app_today
from app.utils.email import send_reminder_digest_email
from app.utils.reminders import (
    build_document_reminders,
    build_service_reminder,
    find_active_next_service,
)

logger = logging.getLogger(__name__)

_DIGEST_TTL_SECONDS = 26 * 60 * 60


@dataclass
class DigestResult:
    users_considered: int
    emails_sent: int
    emails_skipped: int


def _digest_key(user_id: uuid.UUID, day: str) -> str:
    return f"reminder:digest:{user_id}:{day}"


def _doc_type_label(document_type: str) -> str:
    return document_type.replace("_", " ").title()


async def _live_odometers_map(
    db: AsyncSession,
    vehicles: list[Vehicle],
) -> dict[uuid.UUID, int]:
    if not vehicles:
        return {}

    vehicle_ids = [vehicle.id for vehicle in vehicles]
    baselines = {vehicle.id: int(vehicle.current_odometer) for vehicle in vehicles}

    fuel_max = (
        select(
            FuelLog.vehicle_id.label("vehicle_id"),
            func.max(FuelLog.odometer).label("odometer"),
        )
        .where(FuelLog.vehicle_id.in_(vehicle_ids))
        .group_by(FuelLog.vehicle_id)
    )
    service_max = (
        select(
            ServiceLog.vehicle_id.label("vehicle_id"),
            func.max(ServiceLog.odometer).label("odometer"),
        )
        .where(ServiceLog.vehicle_id.in_(vehicle_ids))
        .group_by(ServiceLog.vehicle_id)
    )
    combined = union_all(fuel_max, service_max).subquery()
    result = await db.execute(
        select(
            combined.c.vehicle_id,
            func.max(combined.c.odometer),
        ).group_by(combined.c.vehicle_id)
    )
    log_max = {row[0]: int(row[1] or 0) for row in result.all()}

    return {
        vid: max(baselines[vid], log_max.get(vid, 0)) for vid in vehicle_ids
    }


async def _claim_digest_slot(redis: Redis, user_id: uuid.UUID, day: str) -> bool:
    """Return True if this is the first claim for the user today (NX)."""
    return bool(
        await redis.set(
            _digest_key(user_id, day),
            b"1",
            nx=True,
            ex=_DIGEST_TTL_SECONDS,
        )
    )


async def send_reminder_digests(
    db: AsyncSession,
    redis: Redis,
) -> DigestResult:
    """
    Email verified users who have soon/overdue service or document reminders.

    Idempotent per user per calendar day via Redis.
    """
    today = app_today()
    day = today.isoformat()
    dashboard_url = f"{settings.FRONTEND_URL.rstrip('/')}/"

    users_result = await db.execute(
        select(User)
        .where(User.email_verified.is_(True), User.is_active.is_(True))
        .options(selectinload(User.vehicles))
    )
    users = list(users_result.scalars().unique().all())

    sent = 0
    skipped = 0

    for user in users:
        vehicles = list(user.vehicles)
        if not vehicles:
            skipped += 1
            continue

        live_map = await _live_odometers_map(db, vehicles)
        sections_text: list[str] = []
        sections_html: list[str] = []

        for vehicle in vehicles:
            vehicle_id = vehicle.id
            live_odo = live_map[vehicle_id]

            service_result = await db.execute(
                select(ServiceLog)
                .where(ServiceLog.vehicle_id == vehicle_id)
                .order_by(ServiceLog.date.desc(), ServiceLog.odometer.desc())
            )
            service_logs = list(service_result.scalars().all())
            next_service = find_active_next_service(service_logs)
            service_reminder = build_service_reminder(
                next_service,
                today=today,
                live_odometer=live_odo,
            )

            docs_result = await db.execute(
                select(Document)
                .where(
                    Document.vehicle_id == vehicle_id,
                    Document.expiry_date.is_not(None),
                )
                .order_by(Document.expiry_date.asc())
            )
            documents = list(docs_result.scalars().all())
            document_reminders = build_document_reminders(documents, today=today)

            needs_service = service_reminder.status in ("soon", "overdue")
            if not needs_service and not document_reminders:
                continue

            label = (
                f"{vehicle.brand} {vehicle.vehicle_name}".strip()
                or vehicle.registration_number
            )
            lines: list[str] = [f"{label}:"]
            html_bits: list[str] = [f"<p><strong>{label}</strong></p><ul>"]

            if needs_service:
                parts: list[str] = [f"Service {service_reminder.status}"]
                if service_reminder.days_until is not None:
                    parts.append(f"{service_reminder.days_until} days")
                if service_reminder.km_until is not None:
                    parts.append(f"{service_reminder.km_until} km")
                detail = " · ".join(parts)
                lines.append(f"  - {detail}")
                html_bits.append(f"<li>{detail}</li>")

            for doc in document_reminders:
                detail = (
                    f"{_doc_type_label(doc.document_type)} "
                    f"{doc.status} ({doc.days_until} days)"
                )
                lines.append(f"  - {detail}")
                html_bits.append(f"<li>{detail}</li>")

            html_bits.append("</ul>")
            sections_text.append("\n".join(lines))
            sections_html.append("".join(html_bits))

        if not sections_text:
            skipped += 1
            continue

        if not await _claim_digest_slot(redis, user.id, day):
            skipped += 1
            continue

        await send_reminder_digest_email(
            to=user.email,
            full_name=user.full_name,
            dashboard_url=dashboard_url,
            body_text="\n\n".join(sections_text),
            body_html="".join(sections_html),
        )
        sent += 1
        logger.info("Reminder digest sent to user_id=%s", user.id)

    return DigestResult(
        users_considered=len(users),
        emails_sent=sent,
        emails_skipped=skipped,
    )
