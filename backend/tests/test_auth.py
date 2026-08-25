from httpx import AsyncClient


async def test_register_success(client: AsyncClient):
    """Test the register user endpoint"""
    response = await client.post(
        "/auth/register",
        json={
            "email": "test@ridecare.com",
            "full_name": "Test User",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@ridecare.com"
    assert data["full_name"] == "Test User"
    assert data["email_verified"] is False
    assert "hashed_password" not in data
    assert "id" in data


async def test_register_duplicate_email(client: AsyncClient):
    """Test the register user endpoint with a duplicate email"""
    payload = {
        "email": "test@ridecare.com",
        "full_name": "Test User",
        "password": "TestPassword123!",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201

    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


async def test_login_success(client: AsyncClient, registered_user: dict):
    """Login sets httpOnly cookies; JSON body does not expose tokens."""
    response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


async def test_cookie_auth_protects_routes(client: AsyncClient, registered_user: dict):
    """After login, access cookie alone authorizes API calls (no Authorization header)."""
    login_response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert login_response.status_code == 200

    response = await client.get("/vehicles/")
    assert response.status_code == 200


async def test_refresh_via_cookie(client: AsyncClient, registered_user: dict):
    """Refresh works with the httpOnly refresh cookie and no body token."""
    await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    refresh_response = await client.post("/auth/refresh", json={})
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" not in data
    assert "access_token" in refresh_response.cookies
    assert "refresh_token" in refresh_response.cookies


async def test_logout_clears_cookies(client: AsyncClient, registered_user: dict):
    """Logout revokes the session and clears auth cookies."""
    await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    logout_response = await client.post("/auth/logout", json={})
    assert logout_response.status_code == 204

    refresh_response = await client.post("/auth/refresh", json={})
    assert refresh_response.status_code == 401


async def test_refresh_token_rotation(client: AsyncClient, registered_user: dict):
    """Refresh rotates cookies and invalidates the old refresh token."""
    login_response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    old_refresh = login_response.cookies["refresh_token"]

    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.cookies["refresh_token"]
    assert new_refresh != old_refresh

    reuse_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert reuse_response.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient, registered_user: dict):
    """Logout revokes the refresh token so it cannot be reused."""
    login_response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    refresh_token = login_response.cookies["refresh_token"]

    logout_response = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


async def test_oauth_token_returns_bearer_body(client: AsyncClient, registered_user: dict):
    """Swagger `/auth/token` still returns tokens in the JSON body."""
    response = await client.post(
        "/auth/token",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "access_token" in response.cookies


async def test_login_wrong_password(client: AsyncClient, registered_user: dict):
    """Test the login user endpoint with wrong password"""
    response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401


async def test_login_nonexistent_email(client: AsyncClient):
    """Test the login user endpoint with nonexistent email"""
    response = await client.post(
        "/auth/login",
        json={
            "email": "nonexistent@ridecare.com",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 401


async def test_protected_route_without_token(client: AsyncClient):
    """Test a protected route without a token"""
    response = await client.get("/vehicles/")
    assert response.status_code == 401


async def test_protected_route_with_invalid_token(client: AsyncClient):
    """Test a protected route with an invalid token"""
    response = await client.get(
        "/vehicles/",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


async def test_register_short_password(client: AsyncClient):
    """Test the register user endpoint with a password that is too short"""
    response = await client.post(
        "/auth/register",
        json={
            "email": "shortpass@ridecare.com",
            "full_name": "Test User",
            "password": "short",
        },
    )
    assert response.status_code == 422


async def test_register_weak_password(client: AsyncClient):
    """Reject passwords missing uppercase, number, or special character."""
    response = await client.post(
        "/auth/register",
        json={
            "email": "weakpass@ridecare.com",
            "full_name": "Test User",
            "password": "password123",
        },
    )
    assert response.status_code == 422


async def test_register_invalid_email(client: AsyncClient):
    """Test the register user endpoint with an invalid email"""
    response = await client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "full_name": "Test User",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 422


async def test_logout_blocklists_access_token(
    client: AsyncClient, registered_user: dict
):
    """Logout blocklists the access JWT so Bearer reuse is rejected."""
    login_response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    access_token = login_response.cookies["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    before = await client.get("/users/me", headers=headers)
    assert before.status_code == 200

    logout_response = await client.post("/auth/logout", json={})
    assert logout_response.status_code == 204

    after = await client.get("/users/me", headers=headers)
    assert after.status_code == 401


async def test_refresh_blocklists_old_access_token(
    client: AsyncClient, registered_user: dict
):
    """Refresh rotation blocklists the previous access JWT."""
    login_response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    old_access = login_response.cookies["access_token"]
    headers = {"Authorization": f"Bearer {old_access}"}

    refresh_response = await client.post("/auth/refresh", json={})
    assert refresh_response.status_code == 200

    after = await client.get("/users/me", headers=headers)
    assert after.status_code == 401

    new_access = refresh_response.cookies["access_token"]
    ok = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert ok.status_code == 200


async def test_create_vehicle_without_token(client: AsyncClient):
    """Test creating a vehicle without authentication"""
    response = await client.post(
        "/vehicles/",
        json={
            "brand": "Honda",
            "vehicle_name": "Shine 100",
            "year": 2022,
            "registration_number": "TS09CD5678",
            "baseline_odometer": 3000,
        },
    )
    assert response.status_code == 401


async def test_create_fuel_log_without_token(client: AsyncClient):
    """Test creating a fuel log without authentication"""
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": "00000000-0000-0000-0000-000000000000"},
        json={
            "date": "2024-01-01",
            "odometer": 1000,
            "total_cost": 800,
            "price_per_liter": 110,
        },
    )
    assert response.status_code == 401


async def test_login_blocked_until_email_verified(client: AsyncClient):
    """Unverified accounts cannot log in."""
    payload = {
        "email": "unverified@ridecare.com",
        "full_name": "Unverified User",
        "password": "TestPassword123!",
    }
    register = await client.post("/auth/register", json=payload)
    assert register.status_code == 201
    assert register.json()["email_verified"] is False

    login = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 403
    assert "not verified" in login.json()["detail"].lower()


async def test_verify_email_then_login(client: AsyncClient, monkeypatch):
    """Verification link marks the account verified and unlocks login."""
    captured: dict[str, str] = {}

    async def fake_send(*, to: str, full_name: str, link: str) -> None:
        captured["to"] = to
        captured["link"] = link
        captured["token"] = link.split("token=", 1)[1]

    monkeypatch.setattr("app.routes.auth.send_verification_email", fake_send)

    payload = {
        "email": "verify-me@ridecare.com",
        "full_name": "Verify Me",
        "password": "TestPassword123!",
    }
    register = await client.post("/auth/register", json=payload)
    assert register.status_code == 201
    assert "token" in captured

    verify = await client.post(
        "/auth/verify-email",
        json={"token": captured["token"]},
    )
    assert verify.status_code == 200
    assert "verified" in verify.json()["message"].lower()

    login = await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    assert "access_token" in login.cookies


async def test_verify_email_rejects_bad_token(client: AsyncClient):
    response = await client.post(
        "/auth/verify-email",
        json={"token": "this-token-is-not-valid-at-all"},
    )
    assert response.status_code == 400


async def test_resend_verification_is_generic(client: AsyncClient, monkeypatch):
    """Resend always returns the same message (no email enumeration)."""
    calls: list[str] = []

    async def fake_send(*, to: str, full_name: str, link: str) -> None:
        calls.append(to)

    monkeypatch.setattr("app.routes.auth.send_verification_email", fake_send)

    await client.post(
        "/auth/register",
        json={
            "email": "resend@ridecare.com",
            "full_name": "Resend User",
            "password": "TestPassword123!",
        },
    )
    calls.clear()

    known = await client.post(
        "/auth/resend-verification",
        json={"email": "resend@ridecare.com"},
    )
    unknown = await client.post(
        "/auth/resend-verification",
        json={"email": "nobody@ridecare.com"},
    )
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]
    assert calls == ["resend@ridecare.com"]

