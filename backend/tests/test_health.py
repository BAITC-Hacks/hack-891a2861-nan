import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_liveness_endpoint(client):
    response = client.get(reverse("health-live"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "career-quest-api"}


@pytest.mark.django_db
def test_readiness_endpoint_checks_database(client):
    response = client.get(reverse("health-ready"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


def test_meta_endpoint(client):
    response = client.get(reverse("meta"))

    assert response.status_code == 200
    assert response.json()["api_version"] == "v1"
