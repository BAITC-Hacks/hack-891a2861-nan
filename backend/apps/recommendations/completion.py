from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.activities.models import ActivityHistory
from apps.catalog.models import Event
from apps.employees.models import Employee

CATEGORIES = ("completed", "dropped", "no_show", "declined")
FINAL_STATUSES = set(CATEGORIES)
FEATURES = [
    "employee_role",
    "employee_grade",
    "employee_work_format",
    "employee_preferred_language",
    "event_type",
    "event_format",
    "assigned_by",
    "duration_hours",
    "tenure_days_at_activity",
    "attempt_number",
    "prior_same_event_attempts",
    "employee_prior_outcomes",
    "employee_completion_rate_before",
    "employee_dropped_rate_before",
    "employee_no_show_rate_before",
    "employee_declined_rate_before",
    "employee_format_prior_outcomes",
    "employee_format_completion_rate_before",
    "employee_type_prior_outcomes",
    "employee_type_completion_rate_before",
    "event_prior_outcomes",
    "event_completion_rate_before",
    "is_first_employee_activity",
    "days_since_previous_activity",
]


@lru_cache(maxsize=1)
def _model():
    path = Path(settings.COMPLETION_MODEL_PATH)
    if not path.is_file():
        return None
    try:
        return joblib.load(path)
    except (EOFError, OSError, TypeError, ValueError):
        return None


def _rates(counter: Counter[str]) -> tuple[int, dict[str, float]]:
    total = sum(counter[key] for key in CATEGORIES)
    denominator = total + len(CATEGORIES)
    return total, {key: (counter[key] + 1) / denominator for key in CATEGORIES}


def _completion_rate(counter: Counter[str]) -> tuple[int, float]:
    total = sum(counter[key] for key in CATEGORIES)
    return total, (counter["completed"] + 1) / (total + 2)


def predict_completion_probabilities(
    employee: Employee,
    events: list[Event],
    history: list[ActivityHistory],
) -> dict[str, float]:
    """Predict completion in one batch; use a history-smoothed fallback if ML is unavailable."""
    employee_outcomes: Counter[str] = Counter()
    format_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    type_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    attempts: Counter[str] = Counter()
    last_activity = None
    for activity in history:
        attempts[activity.event_id] += 1
        day = activity.occurred_at.date()
        last_activity = max(last_activity, day) if last_activity else day
        if activity.event.is_mandatory or activity.status not in FINAL_STATUSES:
            continue
        employee_outcomes[activity.status] += 1
        format_outcomes[activity.event.format][activity.status] += 1
        type_outcomes[activity.event.event_type][activity.status] += 1

    event_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    rows = (
        ActivityHistory.objects.filter(event__in=events, status__in=FINAL_STATUSES)
        .values("event_id", "status")
        .annotate(total=Count("id"))
    )
    for row in rows:
        event_outcomes[row["event_id"]][row["status"]] = row["total"]

    employee_count, employee_rates = _rates(employee_outcomes)
    as_of = max(timezone.localdate(), last_activity) if last_activity else timezone.localdate()
    hire_date = employee.hire_date
    tenure_days = (as_of - hire_date).days if hire_date else employee.tenure_months * 30
    feature_rows = []
    fallback = {}
    for event in events:
        format_count, format_rate = _completion_rate(format_outcomes[event.format])
        type_count, type_rate = _completion_rate(type_outcomes[event.event_type])
        event_count, event_rate = _completion_rate(event_outcomes[event.code])
        fallback[event.code] = round((format_rate + type_rate + event_rate) / 3, 4)
        feature_rows.append(
            {
                "employee_role": employee.role.name_en,
                "employee_grade": employee.grade.name_en,
                "employee_work_format": employee.work_format or "unknown",
                "employee_preferred_language": employee.locale,
                "event_type": event.event_type,
                "event_format": event.format,
                "assigned_by": "self",
                "duration_hours": float(event.duration_hours),
                "tenure_days_at_activity": max(tenure_days, 0),
                "attempt_number": attempts[event.code] + 1,
                "prior_same_event_attempts": attempts[event.code],
                "employee_prior_outcomes": employee_count,
                "employee_completion_rate_before": employee_rates["completed"],
                "employee_dropped_rate_before": employee_rates["dropped"],
                "employee_no_show_rate_before": employee_rates["no_show"],
                "employee_declined_rate_before": employee_rates["declined"],
                "employee_format_prior_outcomes": format_count,
                "employee_format_completion_rate_before": format_rate,
                "employee_type_prior_outcomes": type_count,
                "employee_type_completion_rate_before": type_rate,
                "event_prior_outcomes": event_count,
                "event_completion_rate_before": event_rate,
                "is_first_employee_activity": int(last_activity is None),
                "days_since_previous_activity": (
                    -1 if last_activity is None else max((as_of - last_activity).days, 0)
                ),
            }
        )

    model = _model()
    if model is None or not feature_rows:
        return fallback
    try:
        probabilities = model.predict_proba(pd.DataFrame(feature_rows, columns=FEATURES))[:, 1]
    except (TypeError, ValueError):
        return fallback
    return {
        event.code: round(float(probability), 4)
        for event, probability in zip(events, probabilities, strict=True)
    }
