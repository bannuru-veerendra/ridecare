"""Internal reminder digest endpoint tests."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.config import settings
from app.utils.dates import app_today


@pytest.fixture
def cron_secret(monkeypatch):
    monkeypatch.setattr(settings, "REMINDER_CRON_SECRET", "test-cron-secret")
    return "test-cron-secret"


async def test_reminder_digests_disabled_without_secret(client: AsyncClient):
    response = await client.post("/internal/reminder-digests")
    assert response.status_code == 503


async def test_reminder_digests_rejects_bad_secret(
    client: AsyncClient, cron_secret: str
):
    response = await client.post(
        "/internal/reminder-digests",
        headers={"X-Cron-Secret": "wrong"},
    )
    assert response.status_code == 401


async def test_reminder_digests_sends_for_soon_service(
    client: AsyncClient,
    auth_headers: dict,
    created_vehicle: dict,
    cron_secret: str,
    monkeypatch,
):
    send_mock = AsyncMock()
    monkeypatch.setattr(
        "app.utils.reminder_digest.send_reminder_digest_email",
        send_mock,
    )

    vehicle_id = created_vehicle["id"]
    today = app_today()
    await client.post(
        "/service_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(today),
            "odometer": 12000,
            "total_cost": 1500,
            "services_done": ["Engine oil"],
            "next_service_date": str(today + timedelta(days=5)),
        },
        headers=auth_headers,
    )

    response = await client.post(
        "/internal/reminder-digests",
        headers={"X-Cron-Secret": cron_secret},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["emails_sent"] >= 1
    assert send_mock.await_count >= 1

    # Second call same day is deduped
    response2 = await client.post(
        "/internal/reminder-digests",
        headers={"X-Cron-Secret": cron_secret},
    )
    assert response2.status_code == 200
    assert response2.json()["emails_sent"] == 0


async def test_reminder_digests_skips_when_prefs_off(
    client: AsyncClient,
    auth_headers: dict,
    created_vehicle: dict,
    cron_secret: str,
    monkeypatch,
):
    send_mock = AsyncMock()
    monkeypatch.setattr(
        "app.utils.reminder_digest.send_reminder_digest_email",
        send_mock,
    )

    await client.patch(
        "/users/me",
        json={
            "email_service_reminders": False,
            "email_document_reminders": False,
        },
        headers=auth_headers,
    )

    vehicle_id = created_vehicle["id"]
    today = app_today()
    await client.post(
        "/service_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(today),
            "odometer": 12000,
            "total_cost": 1500,
            "services_done": ["Engine oil"],
            "next_service_date": str(today + timedelta(days=5)),
        },
        headers=auth_headers,
    )

    response = await client.post(
        "/internal/reminder-digests",
        headers={"X-Cron-Secret": cron_secret},
    )
    assert response.status_code == 200
    assert response.json()["emails_sent"] == 0
    assert send_mock.await_count == 0


async def test_suggest_next_due_endpoint(
    client: AsyncClient, auth_headers: dict
):
    response = await client.post(
        "/service_logs/suggest-next-due",
        json={
            "date": "2026-01-15",
            "odometer": 10000,
            "services_done": ["Engine Oil"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["next_service_odometer"] == 13000
    assert data["next_service_date"] == "2026-04-15"
    assert "Engine oil change" in data["matched_tasks"]
