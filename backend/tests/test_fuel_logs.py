from datetime import date as dt_date, timedelta

from httpx import AsyncClient

from app.utils.dates import app_today

VEHICLE_ODO = 10000
FIRST_LOG_ODO = 10500
SECOND_LOG_ODO = 11500


async def test_create_fuel_log_first_entry(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint for the first entry"""
    vehicle_id = created_vehicle["id"]
    payload = {
        "date": str(dt_date.today()),
        "odometer": FIRST_LOG_ODO,
        "total_cost": 800,
        "price_per_liter": 110,
    }
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    liters = round(payload["total_cost"] / payload["price_per_liter"], 2)
    expected_mileage = round((FIRST_LOG_ODO - VEHICLE_ODO) / liters, 1)
    assert data["mileage"] == expected_mileage
    assert round(data["liters"], 2) == liters
    assert data["total_cost"] == payload["total_cost"]


async def test_create_fuel_log_second_entry_calculates_mileage(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint for the second entry that calculates mileage"""
    vehicle_id = created_vehicle["id"]

    first_payload = {
        "date": str(dt_date.today()),
        "odometer": FIRST_LOG_ODO,
        "total_cost": 800,
        "price_per_liter": 110,
    }
    await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=first_payload,
        headers=auth_headers,
    )

    second_payload = {
        "date": str(dt_date.today()),
        "odometer": SECOND_LOG_ODO,
        "total_cost": 800,
        "price_per_liter": 110,
    }
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=second_payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    liters = round(
        second_payload["total_cost"] / second_payload["price_per_liter"], 2
    )
    expected_mileage = round((SECOND_LOG_ODO - FIRST_LOG_ODO) / liters, 1)
    assert data["mileage"] == expected_mileage


async def test_create_fuel_log_invalid_cost(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint with an invalid cost"""
    vehicle_id = created_vehicle["id"]
    payload = {
        "date": str(dt_date.today()),
        "odometer": FIRST_LOG_ODO,
        "total_cost": 0,
        "price_per_liter": 110,
    }
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_create_fuel_log_invalid_price_per_liter(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint with an invalid price per liter"""
    vehicle_id = created_vehicle["id"]
    payload = {
        "date": str(dt_date.today()),
        "odometer": FIRST_LOG_ODO,
        "total_cost": 800,
        "price_per_liter": 0,
    }
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_create_fuel_log_invalid_odometer(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint with an invalid odometer"""
    vehicle_id = created_vehicle["id"]
    payload = {
        "date": str(dt_date.today()),
        "odometer": 0,
        "total_cost": 800,
        "price_per_liter": 110,
    }
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_create_fuel_log_rejects_future_date(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint rejects a future date"""
    vehicle_id = created_vehicle["id"]
    payload = {
        "date": str(app_today() + timedelta(days=1)),
        "odometer": FIRST_LOG_ODO,
        "total_cost": 800,
        "price_per_liter": 110,
    }
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_create_fuel_log_odometer_not_greater_than_vehicle(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint rejects odometer at or below vehicle baseline"""
    vehicle_id = created_vehicle["id"]
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": VEHICLE_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "baseline odometer" in response.json()["detail"].lower()


async def test_create_fuel_log_odometer_not_greater_than_previous(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the create fuel log endpoint rejects odometer at or below previous fill-up"""
    vehicle_id = created_vehicle["id"]
    await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today() - timedelta(days=1)),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "previous fill-up" in response.json()["detail"].lower()


async def test_create_fuel_log_missing_vehicle_id(client: AsyncClient, auth_headers: dict):
    """Test the create fuel log endpoint without a vehicle_id query param"""
    response = await client.post(
        "/fuel_logs/",
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_create_fuel_log_mileage_from_vehicle_baseline(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test mileage uses the vehicle odometer when the first log exceeds it"""
    vehicle_id = created_vehicle["id"]
    payload = {
        "date": str(dt_date.today()),
        "odometer": 10500,
        "total_cost": 800,
        "price_per_liter": 110,
    }
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    liters = round(payload["total_cost"] / payload["price_per_liter"], 2)
    expected_mileage = round(
        (10500 - created_vehicle["baseline_odometer"]) / liters, 1
    )
    assert data["mileage"] == expected_mileage


async def test_create_fuel_log_does_not_update_vehicle_baseline(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test creating a fuel log keeps baseline fixed and advances live odometer"""
    vehicle_id = created_vehicle["id"]
    baseline = created_vehicle["baseline_odometer"]
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": 12000,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    vehicle_response = await client.get(f"/vehicles/{vehicle_id}", headers=auth_headers)
    assert vehicle_response.status_code == 200
    assert vehicle_response.json()["baseline_odometer"] == baseline
    assert vehicle_response.json()["current_odometer"] == 12000


async def test_get_fuel_logs(client: AsyncClient, auth_headers: dict, created_vehicle: dict):
    """Test the get fuel logs endpoint"""
    vehicle_id = created_vehicle["id"]
    payload = {
        "date": str(dt_date.today()),
        "odometer": FIRST_LOG_ODO,
        "total_cost": 800,
        "price_per_liter": 110,
    }
    create_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json=payload,
        headers=auth_headers,
    )
    fuel_log_id = create_response.json()["id"]

    response = await client.get(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "has_more" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["id"] == fuel_log_id


async def test_get_fuel_logs_ordered_by_date_desc(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Fuel logs are listed newest date first, even if entered out of order."""
    vehicle_id = created_vehicle["id"]

    await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": SECOND_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today() - timedelta(days=30)),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )

    response = await client.get(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2
    assert data["items"][0]["date"] == str(dt_date.today())
    assert data["items"][0]["odometer"] == SECOND_LOG_ODO
    assert data["items"][1]["date"] == str(dt_date.today() - timedelta(days=30))
    assert data["items"][1]["odometer"] == FIRST_LOG_ODO


async def test_get_fuel_log_by_id(client: AsyncClient, auth_headers: dict, created_vehicle: dict):
    """Test the get fuel log by id endpoint"""
    vehicle_id = created_vehicle["id"]
    create_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    fuel_log_id = create_response.json()["id"]

    response = await client.get(
        f"/fuel_logs/{fuel_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == fuel_log_id


async def test_get_fuel_log_not_found(client: AsyncClient, auth_headers: dict, created_vehicle: dict):
    """Test the get fuel log by id endpoint with a non-existent id"""
    vehicle_id = created_vehicle["id"]
    fuel_log_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(
        f"/fuel_logs/{fuel_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_update_fuel_log_recalculates_mileage(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the update fuel log endpoint recalculates mileage when odometer changes"""
    vehicle_id = created_vehicle["id"]

    await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    create_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": SECOND_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    fuel_log_id = create_response.json()["id"]

    response = await client.patch(
        f"/fuel_logs/{fuel_log_id}",
        params={"vehicle_id": vehicle_id},
        json={"odometer": 12000},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    liters = round(800 / 110, 2)
    expected_mileage = round((12000 - FIRST_LOG_ODO) / liters, 1)
    assert data["mileage"] == expected_mileage


async def test_update_fuel_log_recalculates_subsequent_mileage(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test updating an earlier fill-up recalculates mileage on later entries."""
    vehicle_id = created_vehicle["id"]
    liters = round(800 / 110, 2)

    first_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today() - timedelta(days=1)),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    first_log_id = first_response.json()["id"]

    second_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": SECOND_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    second_log_id = second_response.json()["id"]

    updated_first_odometer = FIRST_LOG_ODO + 300
    response = await client.patch(
        f"/fuel_logs/{first_log_id}",
        params={"vehicle_id": vehicle_id},
        json={"odometer": updated_first_odometer},
        headers=auth_headers,
    )
    assert response.status_code == 200

    second_log_response = await client.get(
        f"/fuel_logs/{second_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    expected_mileage = round(
        (SECOND_LOG_ODO - updated_first_odometer) / liters, 1
    )
    assert second_log_response.json()["mileage"] == expected_mileage


async def test_update_fuel_log_recalculates_total_cost(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Test the update fuel log endpoint recalculates liters when cost changes"""
    vehicle_id = created_vehicle["id"]

    create_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 500,
            "price_per_liter": 100,
        },
        headers=auth_headers,
    )
    fuel_log_id = create_response.json()["id"]

    response = await client.patch(
        f"/fuel_logs/{fuel_log_id}",
        params={"vehicle_id": vehicle_id},
        json={"total_cost": 600},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_cost"] == 600
    assert round(data["liters"], 2) == round(600 / 100, 2)


async def test_delete_fuel_log(client: AsyncClient, auth_headers: dict, created_vehicle: dict):
    """Test the delete fuel log endpoint"""
    vehicle_id = created_vehicle["id"]
    create_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 500,
            "price_per_liter": 105,
        },
        headers=auth_headers,
    )
    fuel_log_id = create_response.json()["id"]

    response = await client.delete(
        f"/fuel_logs/{fuel_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert response.status_code == 204

    response = await client.get(
        f"/fuel_logs/{fuel_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_create_backdated_fuel_log_recalculates_later_mileage(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Inserting an earlier fill-up recalculates mileage on newer entries."""
    vehicle_id = created_vehicle["id"]
    liters = round(800 / 110, 2)

    later_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": SECOND_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    assert later_response.status_code == 201
    later_log_id = later_response.json()["id"]
    assert later_response.json()["mileage"] == round(
        (SECOND_LOG_ODO - VEHICLE_ODO) / liters, 1
    )

    earlier_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today() - timedelta(days=30)),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    assert earlier_response.status_code == 201
    assert earlier_response.json()["mileage"] == round(
        (FIRST_LOG_ODO - VEHICLE_ODO) / liters, 1
    )

    later_log_response = await client.get(
        f"/fuel_logs/{later_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert later_log_response.status_code == 200
    assert later_log_response.json()["mileage"] == round(
        (SECOND_LOG_ODO - FIRST_LOG_ODO) / liters, 1
    )


async def test_create_backdated_fuel_log_rejects_impossible_odometer(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Earlier date with odometer ahead of a newer fill-up is rejected."""
    vehicle_id = created_vehicle["id"]

    await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )

    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today() - timedelta(days=30)),
            "odometer": SECOND_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "previous fill-up" in response.json()["detail"].lower()


async def test_delete_fuel_log_recalculates_subsequent_mileage(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict
):
    """Deleting a middle fill-up recalculates mileage on later entries."""
    vehicle_id = created_vehicle["id"]
    liters = round(800 / 110, 2)

    first_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today() - timedelta(days=2)),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    first_log_id = first_response.json()["id"]

    await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today() - timedelta(days=1)),
            "odometer": FIRST_LOG_ODO + 400,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )

    third_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": SECOND_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    third_log_id = third_response.json()["id"]

    middle_logs = await client.get(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    middle_log_id = next(
        log["id"]
        for log in middle_logs.json()["items"]
        if log["id"] not in {first_log_id, third_log_id}
    )

    delete_response = await client.delete(
        f"/fuel_logs/{middle_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    third_log_response = await client.get(
        f"/fuel_logs/{third_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=auth_headers,
    )
    assert third_log_response.status_code == 200
    assert third_log_response.json()["mileage"] == round(
        (SECOND_LOG_ODO - FIRST_LOG_ODO) / liters, 1
    )


async def test_fuel_log_wrong_vehicle(client: AsyncClient, auth_headers: dict):
    """Test creating a fuel log for a non-existent vehicle returns 404"""
    fake_vehicle_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": fake_vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 500,
            "price_per_liter": 105,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_cannot_access_other_users_fuel_logs(
    client: AsyncClient, created_vehicle: dict, other_user_headers: dict
):
    """Test that a user cannot access another user's fuel logs"""
    vehicle_id = created_vehicle["id"]
    response = await client.get(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        headers=other_user_headers,
    )
    assert response.status_code == 404


async def test_cannot_get_other_users_fuel_log_by_id(
    client: AsyncClient, auth_headers: dict, created_vehicle: dict, other_user_headers: dict
):
    """Test that a user cannot get another user's fuel log by id"""
    vehicle_id = created_vehicle["id"]
    create_response = await client.post(
        "/fuel_logs/",
        params={"vehicle_id": vehicle_id},
        json={
            "date": str(dt_date.today()),
            "odometer": FIRST_LOG_ODO,
            "total_cost": 800,
            "price_per_liter": 110,
        },
        headers=auth_headers,
    )
    fuel_log_id = create_response.json()["id"]

    response = await client.get(
        f"/fuel_logs/{fuel_log_id}",
        params={"vehicle_id": vehicle_id},
        headers=other_user_headers,
    )
    assert response.status_code == 404
