from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from apps.employees.models import Employee
from apps.recommendations.engine import recommend
from apps.recommendations.explainer import explain_recommendations


@pytest.fixture
def demo_data(db):
    call_command("seed_demo", verbosity=0)


def _context():
    employee = SimpleNamespace(
        role=SimpleNamespace(name_en="Backend Engineer"),
        grade=SimpleNamespace(name_en="Middle"),
    )
    target = SimpleNamespace(
        role=SimpleNamespace(name_en="Backend Engineer"),
        name_en="Senior",
    )
    recommendations = []
    for rank in range(1, 4):
        recommendations.append(
            {
                "rank": rank,
                "event": {"code": f"EV_{rank:03d}"},
                "evidence": {
                    "grade": "Middle → Senior",
                    "skill_gaps": [
                        {
                            "skill_code": "SK_SYSTEM_DESIGN",
                            "current_level": 2,
                            "required_level": 4,
                            "gain": 1,
                            "max_level": 5,
                        }
                    ],
                    "history": {"similar_completed": 0, "similar_not_completed": 2},
                    "completion_probability": 0.75,
                },
                "explanation": {
                    "summary": "Grounded fallback",
                    "reasons": [
                        {"factor": "grade", "message": "Middle → Senior"},
                        {"factor": "skill_gap", "message": "System Design: 2 / 4"},
                        {"factor": "history", "message": "2 similar activities not completed"},
                    ],
                },
            }
        )
    return employee, target, recommendations


def _valid_response(recommendations, prefix="Explanation"):
    return {
        "recommendations": [
            {
                "event_id": item["event"]["code"],
                "summary": f"{prefix} {item['rank']}",
                "reasons": [
                    {"factor": "grade", "message": "Middle to Senior"},
                    {"factor": "skill_gap", "message": "Relevant skill gap"},
                    {"factor": "history", "message": "History considered neutrally"},
                ],
            }
            for item in recommendations
        ]
    }


@pytest.mark.django_db
def test_normal_backend_engineer_recommendation(demo_data):
    result = recommend(Employee.objects.get(pk="E0041"), "en", persist=False, use_ml=False)
    assert result and result[0]["event"]["code"]


@pytest.mark.django_db
def test_critical_skill_gap_remains_dominant(demo_data):
    result = recommend(Employee.objects.get(pk="E0028"), "en", persist=False, use_ml=False)
    assert result[0]["event"]["code"] in {"EV_SYSTEM_DESIGN", "EV_ARCH_PROJECT"}


@pytest.mark.django_db
def test_no_relevant_history_is_explicit(demo_data):
    employee = Employee.objects.get(pk="E0063")
    employee.activities.all().delete()
    result = recommend(employee, "en", persist=False, use_ml=False)
    history = next(x for x in result[0]["explanation"]["reasons"] if x["factor"] == "history")
    assert "0 completed, 0 not completed" in history["message"]


@pytest.mark.django_db
def test_negative_history_is_neutral(demo_data):
    result = recommend(Employee.objects.get(pk="E0028"), "en", persist=False, use_ml=False)
    rendered = str(result)
    assert "not completed" in rendered
    assert "failure" not in rendered.lower()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "phrase"),
    [("en", "Similar activities"), ("ru", "Похожие активности"), ("kk", "Ұқсас белсенділіктер")],
)
def test_fallback_languages(demo_data, monkeypatch, language, phrase):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = recommend(
        Employee.objects.get(pk="E0028"), language, persist=False, use_ml=False
    )
    assert phrase in str(result)


def test_missing_api_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    employee, target, recommendations = _context()
    result = explain_recommendations(employee, target, recommendations, "en")
    assert result.source == "fallback"


def test_openai_exception_uses_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    employee, target, recommendations = _context()
    with patch("apps.recommendations.explainer._call_openai", side_effect=TimeoutError):
        result = explain_recommendations(employee, target, recommendations, "en")
    assert result.source == "fallback"


def test_llm_cannot_change_event_ids_or_order(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    employee, target, recommendations = _context()
    changed = _valid_response(list(reversed(recommendations)))
    with patch("apps.recommendations.explainer._call_openai", return_value=changed):
        result = explain_recommendations(employee, target, recommendations, "en")
    assert result.source == "fallback"


def test_llm_cannot_fabricate_skill_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    employee, target, recommendations = _context()
    fabricated = _valid_response(recommendations)
    fabricated["recommendations"][0]["summary"] = "Skill level is 99"
    with patch("apps.recommendations.explainer._call_openai", return_value=fabricated):
        result = explain_recommendations(employee, target, recommendations, "en")
    assert result.source == "fallback"


def test_top_three_use_one_openai_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    employee, target, recommendations = _context()
    mocked = Mock(return_value=_valid_response(recommendations))
    with patch("apps.recommendations.explainer._call_openai", mocked):
        result = explain_recommendations(employee, target, recommendations, "en")
    assert mocked.call_count == 1
    assert result.source == "openai"
    assert len(result.explanations) == 3
