
from fastapi.testclient import TestClient

from app.main import app


def test_create_account_rejects_blank_owner_name():
    with TestClient(app) as client:
        response = client.post(
            "/accounts",
            json={
                "owner_name": "   ",
                "opening_balance": 100.00,
            },
        )

    assert response.status_code == 422


def test_create_account_rejects_negative_balance():
    with TestClient(app) as client:
        response = client.post(
            "/accounts",
            json={
                "owner_name": "Test User",
                "opening_balance": -10.00,
            },
        )

    assert response.status_code == 422


def test_create_account_rejects_excess_decimal_places():
    with TestClient(app) as client:
        response = client.post(
            "/accounts",
            json={
                "owner_name": "Test User",
                "opening_balance": 10.123,
            },
        )

    assert response.status_code == 422
