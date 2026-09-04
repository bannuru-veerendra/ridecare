from httpx import AsyncClient


async def test_get_profile(client: AsyncClient, auth_headers: dict, registered_user: dict):
    """Test the get profile endpoint"""
    response = await client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == registered_user["email"]
    assert data["full_name"] == "Test User"
    assert "hashed_password" not in data
    assert "id" in data


async def test_get_profile_cached(
    client: AsyncClient, auth_headers: dict, registered_user: dict
):
    """Second GET /users/me reuses the identity cache."""
    first = await client.get("/users/me", headers=auth_headers)
    second = await client.get("/users/me", headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert second.json()["email"] == registered_user["email"]


async def test_get_profile_without_token(client: AsyncClient):
    """Test the get profile endpoint without a token"""
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_update_full_name(client: AsyncClient, auth_headers: dict):
    """Test updating the current user's full name"""
    response = await client.patch(
        "/users/me",
        json={"full_name": "Veerendra Bannuru"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Veerendra Bannuru"


async def test_profile_update_visible_on_next_get(
    client: AsyncClient, auth_headers: dict
):
    """Identity cache is replaced so the next GET shows the new name."""
    await client.get("/users/me", headers=auth_headers)
    await client.patch(
        "/users/me",
        json={"full_name": "Cached Name"},
        headers=auth_headers,
    )
    response = await client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Cached Name"


async def test_update_email(client: AsyncClient, auth_headers: dict):
    """Test updating the current user's email"""
    response = await client.patch(
        "/users/me",
        json={"email": "newemail@ridecare.com"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["email"] == "newemail@ridecare.com"
    assert response.json()["email_verified"] is False


async def test_update_email_conflict(
    client: AsyncClient,
    auth_headers: dict,
    other_user_headers: dict,
):
    """Test updating email to one already used by another account"""
    other_profile = await client.get("/users/me", headers=other_user_headers)
    other_email = other_profile.json()["email"]

    response = await client.patch(
        "/users/me",
        json={"email": other_email},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


async def test_update_email_same_as_current(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: dict,
):
    """Test updating email to the same value succeeds without conflict"""
    response = await client.patch(
        "/users/me",
        json={"email": registered_user["email"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["email"] == registered_user["email"]


async def test_update_profile_empty_body(client: AsyncClient, auth_headers: dict):
    """Test that an empty update body is rejected"""
    response = await client.patch(
        "/users/me",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_update_full_name_too_short(client: AsyncClient, auth_headers: dict):
    """Test that a full name under 2 characters is rejected"""
    response = await client.patch(
        "/users/me",
        json={"full_name": "A"},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_update_invalid_email(client: AsyncClient, auth_headers: dict):
    """Test that an invalid email format is rejected"""
    response = await client.patch(
        "/users/me",
        json={"email": "not-an-email"},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_change_password_success(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: dict,
):
    """Test changing password returns 204 and allows login with the new password"""
    response = await client.patch(
        "/users/me/password",
        json={
            "current_password": registered_user["password"],
            "new_password": "NewPassword456@",
            "confirm_password": "NewPassword456@",
        },
        headers=auth_headers,
    )
    assert response.status_code == 204

    login_response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": "NewPassword456@",
        },
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies


async def test_change_password_wrong_current(client: AsyncClient, auth_headers: dict):
    """Test changing password with the wrong current password"""
    response = await client.patch(
        "/users/me/password",
        json={
            "current_password": "WrongPassword999!",
            "new_password": "NewPassword456@",
            "confirm_password": "NewPassword456@",
        },
        headers=auth_headers,
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


async def test_change_password_mismatch(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: dict,
):
    """Test that mismatched new passwords are rejected"""
    response = await client.patch(
        "/users/me/password",
        json={
            "current_password": registered_user["password"],
            "new_password": "NewPassword456@",
            "confirm_password": "DifferentPassword789@",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_change_password_same_as_current(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: dict,
):
    """Test that reusing the current password is rejected"""
    response = await client.patch(
        "/users/me/password",
        json={
            "current_password": registered_user["password"],
            "new_password": registered_user["password"],
            "confirm_password": registered_user["password"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_change_password_weak(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: dict,
):
    """Test that a weak new password is rejected"""
    response = await client.patch(
        "/users/me/password",
        json={
            "current_password": registered_user["password"],
            "new_password": "weakpassword",
            "confirm_password": "weakpassword",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_change_password_revokes_sessions(
    client: AsyncClient,
    registered_user: dict,
):
    """After password change, old refresh tokens cannot be reused"""
    login_response = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    access_token = login_response.cookies["access_token"]
    refresh_token = login_response.cookies["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    change_response = await client.patch(
        "/users/me/password",
        json={
            "current_password": registered_user["password"],
            "new_password": "NewPassword456@",
            "confirm_password": "NewPassword456@",
        },
        headers=headers,
    )
    assert change_response.status_code == 204

    cookie_headers = change_response.headers.get_list("set-cookie")
    assert any("access_token" in header for header in cookie_headers)
    assert any("refresh_token" in header for header in cookie_headers)

    refresh_response = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401

    # Old access JWT is also dead via revoke-epoch
    me_response = await client.get("/users/me", headers=headers)
    assert me_response.status_code == 401


async def test_update_reminder_preferences(client: AsyncClient, auth_headers: dict):
    """Toggle service and document reminder email prefs."""
    response = await client.patch(
        "/users/me",
        json={
            "email_service_reminders": False,
            "email_document_reminders": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_service_reminders"] is False
    assert data["email_document_reminders"] is False

    again = await client.get("/users/me", headers=auth_headers)
    assert again.status_code == 200
    assert again.json()["email_service_reminders"] is False
    assert again.json()["email_document_reminders"] is False


async def test_delete_account_requires_password(
    client: AsyncClient, auth_headers: dict
):
    response = await client.request(
        "DELETE",
        "/users/me",
        json={"password": "WrongPassword1!"},
        headers=auth_headers,
    )
    assert response.status_code == 401


async def test_delete_account_success(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: dict,
    created_vehicle: dict,
):
    """Deleting the account removes the user and clears auth."""
    _ = created_vehicle
    response = await client.request(
        "DELETE",
        "/users/me",
        json={"password": registered_user["password"]},
        headers=auth_headers,
    )
    assert response.status_code == 204

    me = await client.get("/users/me", headers=auth_headers)
    assert me.status_code == 401

    login = await client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert login.status_code in (401, 403)
