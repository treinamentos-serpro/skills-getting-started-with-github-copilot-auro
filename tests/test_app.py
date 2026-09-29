import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CANCELLATION_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setattr(
        app_module,
        "activities",
        {
            "Chess Club": {
                "description": "Learn chess",
                "schedule": "Fridays",
                "max_participants": 2,
                "participants": ["current@school.edu"],
            },
            "Full Club": {
                "description": "A full activity",
                "schedule": "Mondays",
                "max_participants": 1,
                "participants": ["only@school.edu"],
            },
        },
    )

    with TestClient(app_module.app) as test_client:
        yield test_client


def test_get_activities_returns_activity_data(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json()["Chess Club"]["participants"] == ["current@school.edu"]


def test_signup_adds_participant(client):
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": "new@school.edu"},
    )

    assert response.status_code == 200
    assert "new@school.edu" in client.get("/activities").json()["Chess Club"]["participants"]


def test_signup_returns_404_for_missing_activity(client):
    response = client.post(
        "/activities/Unknown Club/signup",
        params={"email": "new@school.edu"},
    )

    assert response.status_code == 404


def test_signup_returns_400_for_duplicate_participant(client):
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": "current@school.edu"},
    )

    assert response.status_code == 400


def test_signup_returns_400_when_activity_is_full(client):
    response = client.post(
        "/activities/Full Club/signup",
        params={"email": "new@school.edu"},
    )

    assert response.status_code == 400


def test_cancel_signup_removes_participant(client):
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "current@school.edu"},
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 200
    assert "current@school.edu" not in client.get("/activities").json()["Chess Club"]["participants"]


def test_cancel_signup_returns_404_for_missing_activity(client):
    response = client.delete(
        "/activities/Unknown Club/signup",
        params={"email": "student@school.edu"},
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 404


def test_cancel_signup_returns_404_for_unregistered_participant(client):
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "unknown@school.edu"},
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 404


def test_cancel_signup_requires_admin_authentication(client):
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "current@school.edu"},
    )

    assert response.status_code == 401
    assert "current@school.edu" in client.get("/activities").json()["Chess Club"]["participants"]