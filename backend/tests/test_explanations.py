from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from apps.employees.models import Employee
from apps.employees.services import next_grade_for
from apps.recommendations.engine import recommend
from apps.recommendations.llm import (
    RecommendationExplanation,
    build_evidence,
    explain_recommendations,
    fallback_explanation,
)


@pytest.fixture
def evidence(db):
    call_command("seed_demo", verbosity=0)
    employee = Employee.objects.select_related("role", "grade").get(pk="E0028")
    recommendations = recommend(employee, "en", persist=False)
    history = list(
        employee.activities.select_related("event")
        .prefetch_related("event__skill_gains")
        .order_by("-occurred_at")
    )
    return build_evidence(employee, next_grade_for(employee), recommendations, history, "en")


def test_backend_engineer_evidence_and_fallback(evidence, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert evidence["employee"]["role"] == "Backend Engineer"
    assert 1 <= len(evidence["recommendations"]) <= 3
    first = evidence["recommendations"][0]
    skill = first["affected_target_skills"][0]
    assert skill["gap"] == skill["required"] - skill["current"]
    assert skill["projected_after_completion"] == skill["current"] + skill["achievable_gain"]
    assert isinstance(skill["critical"], bool)
    assert first["prerequisites_met"] is True
    result = explain_recommendations(evidence)
    assert result.recommendations[0].event_id == first["event_id"]
    assert str(skill["current"]) in result.recommendations[0].why_recommended
    assert str(skill["required"]) in result.recommendations[0].why_recommended


@pytest.mark.parametrize("language,word", [
    ("en", "requires"), ("ru", "требуется"), ("kk", "қажет"),
])
def test_fallback_languages(evidence, monkeypatch, language, word):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evidence["language"] = language
    result = explain_recommendations(evidence)
    assert word in result.recommendations[0].why_recommended


def test_no_history_and_negative_history_are_neutral(evidence, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evidence["recommendations"][0]["relevant_history"] = []
    assert explain_recommendations(evidence).recommendations[0].history_context is None
    evidence["recommendations"][0]["relevant_history"] = [
        {"event_title": "Speaking", "status": "declined"}
    ]
    context = explain_recommendations(evidence).recommendations[0].history_context
    assert "declined" in context
    assert "failed" not in context


def test_api_exception_falls_back(evidence, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    with patch("apps.recommendations.llm.OpenAI", side_effect=TimeoutError):
        result = explain_recommendations(evidence)
    assert result.recommendations[0].event_id == evidence["recommendations"][0]["event_id"]


def test_one_request_for_top_three(evidence, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    cache.clear()
    cards = fallback_explanation(evidence).model_dump()
    parsed = RecommendationExplanation.model_validate(cards)
    with patch("apps.recommendations.llm.OpenAI") as client:
        client.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
        result = explain_recommendations(evidence)
    assert client.return_value.responses.parse.call_count == 1
    assert len(result.recommendations) == len(evidence["recommendations"])


@pytest.mark.parametrize("mutation", ["identity", "rank", "number", "history"])
def test_invalid_model_claims_fall_back(evidence, monkeypatch, mutation):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    cache.clear()
    parsed = fallback_explanation(evidence).model_dump()
    if mutation == "identity":
        parsed["recommendations"][0]["event_id"] = "EV_FAKE"
    elif mutation == "rank":
        parsed["recommendations"][0]["rank"] = 99
    elif mutation == "number":
        parsed["recommendations"][0]["expected_impact"] = "Will reach level 99."
    else:
        evidence["recommendations"][0]["relevant_history"] = []
        parsed["recommendations"][0]["history_context"] = "Completed a course."
    with patch("apps.recommendations.llm.OpenAI") as client:
        client.return_value.responses.parse.return_value = SimpleNamespace(
            output_parsed=RecommendationExplanation.model_validate(parsed)
        )
        result = explain_recommendations(evidence)
    assert result.recommendations[0].event_id == evidence["recommendations"][0]["event_id"]
    assert "99" not in result.recommendations[0].expected_impact
    if mutation == "history":
        assert result.recommendations[0].history_context is None


@override_settings(DEMO_MODE=True)
def test_endpoint_exposes_explanation_without_key(client, db, monkeypatch):
    call_command("seed_demo", verbosity=0)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.get(
        reverse("employee-recommendations", kwargs={"employee_id": "E0028"}),
        HTTP_X_EMPLOYEE_ID="E0028",
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["event"]["code"] for item in payload["recommendations"]] == [
        item["event_id"] for item in payload["ai_explanation"]["recommendations"]
    ]
