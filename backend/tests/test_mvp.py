import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from apps.catalog.models import Event
from apps.employees.models import Employee
from apps.recommendations.engine import recommend


@pytest.fixture
def demo_data(db):
    call_command("seed_demo", verbosity=0)


def test_adversarial_profile_prioritises_critical_grade_gap(demo_data):
    employee = Employee.objects.get(pk="E0028")

    result = recommend(employee, "en")

    assert 1 <= len(result) <= 3
    assert result[0]["event"]["code"] in {"EV_SYSTEM_DESIGN", "EV_ARCH_PROJECT"}
    assert result[0]["event"]["code"] != "EV_SPEAKING"
    factors = {reason["factor"] for reason in result[0]["explanation"]["reasons"]}
    assert {"grade", "skill_gap", "history"}.issubset(factors)


@override_settings(DEMO_MODE=True)
def test_complete_activity_updates_skill_and_trajectory(client, demo_data):
    employee = Employee.objects.get(pk="E0028")
    before = employee.skill_levels.get(skill_id="SK_SYSTEM_DESIGN").level
    url = reverse(
        "activity-complete",
        kwargs={"employee_id": employee.pk, "event_id": "EV_SYSTEM_DESIGN"},
    )

    response = client.post(
        url,
        data={},
        content_type="application/json",
        HTTP_X_EMPLOYEE_ID=employee.pk,
        HTTP_IDEMPOTENCY_KEY="test-completion-1",
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.skill_levels.get(skill_id="SK_SYSTEM_DESIGN").level == before + 1
    assert response.json()["trajectory"]["readiness_percent"] > 0


@override_settings(DEMO_MODE=True)
def test_completion_is_idempotent(client, demo_data):
    url = reverse(
        "activity-complete", kwargs={"employee_id": "E0028", "event_id": "EV_SYSTEM_DESIGN"}
    )
    headers = {"HTTP_X_EMPLOYEE_ID": "E0028", "HTTP_IDEMPOTENCY_KEY": "same-key"}

    first = client.post(url, data={}, content_type="application/json", **headers)
    second = client.post(url, data={}, content_type="application/json", **headers)

    assert first.status_code == second.status_code == 200
    assert first.json()["activity_id"] == second.json()["activity_id"]


@override_settings(DEMO_MODE=True)
def test_hr_dashboard_contains_required_views(client, demo_data):
    response = client.get(reverse("hr-dashboard"), HTTP_X_DEMO_ROLE="hr")

    assert response.status_code == 200
    payload = response.json()
    assert payload["top_skill_gaps"]
    assert "employees_without_step" in payload
    assert payload["participation"]


@override_settings(DEMO_MODE=False)
def test_employee_data_requires_authentication_outside_demo(client, db):
    response = client.get(reverse("employee-list"))

    assert response.status_code in {401, 403}


def test_seed_has_only_voluntary_recommendation_events(demo_data):
    assert not Event.objects.filter(is_mandatory=True).exists()
