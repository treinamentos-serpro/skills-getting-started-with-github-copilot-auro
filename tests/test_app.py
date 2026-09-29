from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
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


def test_concurrent_signups_respect_activity_capacity(client):
    def signup():
        return client.post(
            "/activities/Chess Club/signup",
            params={"email": "new@school.edu"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: signup(), range(2)))

    assert sorted(response.status_code for response in responses) == [200, 400]
    assert client.get("/activities").json()["Chess Club"]["participants"].count("new@school.edu") == 1


def test_cancel_signup_removes_participant(client):
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "current@school.edu"},
    )

    assert response.status_code == 200
    assert "current@school.edu" not in client.get("/activities").json()["Chess Club"]["participants"]


def test_cancel_signup_returns_404_for_missing_activity(client):
    response = client.delete(
        "/activities/Unknown Club/signup",
        params={"email": "student@school.edu"},
    )

    assert response.status_code == 404


def test_cancel_signup_returns_404_for_unregistered_participant(client):
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "unknown@school.edu"},
    )

    assert response.status_code == 404