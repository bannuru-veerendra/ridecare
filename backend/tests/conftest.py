from __future__ import annotations

import os

os.environ["ENV_FILE"] = ".env.test"

import io
import uuid

import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.models.fuel_log import FuelLog
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.service_log import ServiceLog
from app.models.document import Document
from app.utils.redis_client import get_redis
from main import app


class FakeRedis:
    """In-memory Redis stand-in for auth refresh-token tests."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._sets: dict[str, set[bytes]] = {}

    def _as_bytes(self, value: str | bytes) -> bytes:
        return value if isinstance(value, bytes) else value.encode()

    async def setex(self, name: str, time: int, value: str | bytes) -> bool:
        self._store[name] = self._as_bytes(value)
        return True

    async def set(
        self,
        name: str,
        value: str | bytes,
        nx: bool = False,
        ex: int | None = None,
        **kwargs,
    ):
        """Minimal Redis SET supporting NX (used by reminder digest dedupe)."""
        _ = ex, kwargs
        if nx and name in self._store:
            return None
        self._store[name] = self._as_bytes(value)
        return True

    async def get(self, name: str) -> bytes | None:
        """Get a value without deleting it."""
        return self._store.get(name)

    async def exists(self, *names: str) -> int:
        """Return how many of the given keys exist."""
        return sum(1 for name in names if name in self._store)

    async def getdel(self, name: str) -> bytes | None:
        return self._store.pop(name, None)

    async def scan_iter(self, pattern: str = "*"):
        """Yield keys matching a glob pattern."""
        import fnmatch

        for key in list(self._store.keys()):
            if fnmatch.fnmatch(key, pattern):
                yield key

    async def delete(self, *names: str) -> int:
        deleted = 0
        for name in names:
            if name in self._store:
                del self._store[name]
                deleted += 1
            if name in self._sets:
                del self._sets[name]
                deleted += 1
        return deleted

    async def sadd(self, name: str, *values: str | bytes) -> int:
        bucket = self._sets.setdefault(name, set())
        before = len(bucket)
        for value in values:
            bucket.add(self._as_bytes(value))
        return len(bucket) - before

    async def srem(self, name: str, *values: str | bytes) -> int:
        bucket = self._sets.get(name)
        if not bucket:
            return 0
        removed = 0
        for value in values:
            encoded = self._as_bytes(value)
            if encoded in bucket:
                bucket.remove(encoded)
                removed += 1
        return removed

    async def smembers(self, name: str) -> set[bytes]:
        return set(self._sets.get(name, set()))

    async def incr(self, name: str) -> int:
        """Increment counter, initialize to 0 if not exists."""
        current = self._store.get(name, b"0")
        new_value = int(current) + 1
        self._store[name] = str(new_value).encode()
        return new_value

    async def expire(self, name: str, time: int) -> bool:
        return name in self._store or name in self._sets

    def pipeline(self, transaction: bool = True, **kwargs):
        return FakePipeline(self)

    async def aclose(self) -> None:
        return None


class FakePipeline:
    """Queues FakeRedis commands and runs them on execute()."""

    def __init__(self, redis: FakeRedis) -> None:
        self._redis = redis
        self._ops: list[tuple] = []

    def incr(self, name: str):
        self._ops.append(("incr", name))
        return self

    def get(self, name: str):
        self._ops.append(("get", name))
        return self

    async def execute(self):
        results = []
        for op, name in self._ops:
            if op == "incr":
                results.append(await self._redis.incr(name))
            elif op == "get":
                results.append(await self._redis.get(name))
        self._ops.clear()
        return results


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_maker(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def mock_document_storage(monkeypatch):
    """Mock Supabase storage so document tests run without external services."""

    async def fake_upload_document(file, vehicle_id, document_type):
        from app.utils.storage import ALLOWED_CONTENT_TYPES

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF, JPEG, JPG, and PNG files are allowed",
            )
        filename = file.filename or "file"
        extension = filename.rsplit(".", 1)[-1].lower()
        return f"{vehicle_id}/{document_type}_{uuid.uuid4()}.{extension}"

    async def fake_get_signed_url(storage_path, expires_in=3600):
        return f"https://fake-storage.example.com/{storage_path}?expires_in={expires_in}"

    async def fake_cleanup_document(path):
        return None

    async def fake_delete_document(path):
        return None

    async def fake_move_document(from_path, to_path):
        return to_path

    async def fake_relocate_document_type(storage_path, vehicle_id, new_document_type):
        extension = storage_path.rsplit(".", 1)[-1].lower()
        return f"{vehicle_id}/{new_document_type}_{uuid.uuid4()}.{extension}"

    for module in ("app.utils.storage", "app.routes.documents"):
        monkeypatch.setattr(f"{module}.upload_document", fake_upload_document)
        monkeypatch.setattr(f"{module}.get_signed_url", fake_get_signed_url)
        monkeypatch.setattr(f"{module}.cleanup_document", fake_cleanup_document)
        monkeypatch.setattr(f"{module}.move_document", fake_move_document)
        monkeypatch.setattr(f"{module}.relocate_document_type", fake_relocate_document_type)

    monkeypatch.setattr("app.utils.storage.delete_document", fake_delete_document)
    monkeypatch.setattr("app.routes.documents.delete_storage_document", fake_delete_document)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(test_session_maker):
    async with test_session_maker() as session:
        await session.execute(delete(Document))
        await session.execute(delete(FuelLog))
        await session.execute(delete(ServiceLog))
        await session.execute(delete(Vehicle))
        await session.execute(delete(User))
        await session.commit()
    yield
    async with test_session_maker() as session:
        await session.execute(delete(Document))
        await session.execute(delete(FuelLog))
        await session.execute(delete(ServiceLog))
        await session.execute(delete(Vehicle))
        await session.execute(delete(User))
        await session.commit()


@pytest_asyncio.fixture
async def client(test_session_maker, monkeypatch):
    async def override_get_db():
        async with test_session_maker() as session:
            yield session

    fake_redis = FakeRedis()

    # Middleware calls get_redis() directly (not via Depends), so patch both.
    monkeypatch.setattr("app.utils.redis_client.get_redis", lambda: fake_redis)
    monkeypatch.setattr("main.get_redis", lambda: fake_redis)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient, test_session_maker):
    """Create a verified user and return their credentials"""
    payload = {
        "email": "test@ridecare.com",
        "full_name": "Test User",
        "password": "TestPassword123!",
    }
    await client.post("/auth/register", json=payload)
    async with test_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == payload["email"])
        )
        user = result.scalar_one()
        user.email_verified = True
        await session.commit()
    return payload


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user: dict):
    """Authenticate and return Bearer headers (cookies cleared so unauth tests stay clean)."""
    response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    access = response.cookies["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {access}"}


@pytest_asyncio.fixture
async def other_user_headers(client: AsyncClient, test_session_maker):
    """Register a second verified user and return their auth headers"""
    payload = {
        "email": "otheruser@ridecare.com",
        "full_name": "Other User",
        "password": "OtherPass123!",
    }
    await client.post("/auth/register", json=payload)
    async with test_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == payload["email"])
        )
        user = result.scalar_one()
        user.email_verified = True
        await session.commit()
    login_response = await client.post(
        "/auth/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
        },
    )

    access = login_response.cookies["access_token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {access}"}


@pytest_asyncio.fixture
async def created_vehicle(client: AsyncClient, auth_headers: dict):
    """Create a vehicle and return its response"""
    payload = {
        "brand": "Test Brand",
        "vehicle_name": "Test Vehicle",
        "year": 2020,
        "registration_number": "1234567890",
        "baseline_odometer": 10000,
    }
    response = await client.post("/vehicles/", json=payload, headers=auth_headers)
    return response.json()


@pytest_asyncio.fixture
async def created_document(client: AsyncClient, auth_headers: dict, created_vehicle: dict):
    """Create a document and return its response"""
    vehicle_id = created_vehicle["id"]
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content for testing")
    fake_pdf.name = "test_document.pdf"

    response = await client.post(
        "/documents/",
        params={"vehicle_id": vehicle_id},
        data={
            "document_type": "insurance",
            "expiry_date": "2026-01-01",
            "notes": "Test document",
        },
        files={"file": ("test_document.pdf", fake_pdf, "application/pdf")},
        headers=auth_headers,
    )
    return response.json()
