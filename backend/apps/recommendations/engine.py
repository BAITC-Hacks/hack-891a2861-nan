import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date

from django.db.models import Prefetch

from apps.activities.models import ActivityHistory
from apps.catalog.models import Event, EventSkillGain, GradeRequirement
from apps.employees.models import Employee
from apps.employees.services import next_grade_for
from apps.recommendations.models import RecommendationSnapshot
from apps.recommendations.scoring import ScoreBreakdown

ENGINE_VERSION = "hybrid-v1"


@dataclass
class Candidate:
    event: Event
    score: ScoreBreakdown
    impacted_skills: list[dict]
    completed_similar: int
    skipped_similar: int


def _eligible_events(employee: Employee) -> list[Event]:
    today = date.today()
    completed_ids = set(
        employee.activities.filter(status=ActivityHistory.Status.COMPLETED).values_list(
            "event_id", flat=True
        )
    )
    queryset = (
        Event.objects.filter(is_active=True, is_mandatory=False)
        .prefetch_related(
            "audience_roles",
            "audience_grades",
            Prefetch("skill_gains", queryset=EventSkillGain.objects.select_related("skill")),
        )
        .order_by("code")
    )
    eligible = []
    for event in queryset:
        if event.available_from and event.available_from > today:
            continue
        if event.available_until and event.available_until < today:
            continue
        role_ids = {role.code for role in event.audience_roles.all()}
        grade_ids = {grade.id for grade in event.audience_grades.all()}
        if role_ids and employee.role_id not in role_ids:
            continue
        if grade_ids and employee.grade_id not in grade_ids:
            continue
        if event.code in completed_ids and not event.repeatable:
            continue
        levels = dict(employee.skill_levels.values_list("skill_id", "level"))
        if any(levels.get(code, 0) < level for code, level in event.prerequisites.items()):
            continue
        eligible.append(event)
    return eligible


def _context_hash(employee: Employee) -> str:
    state = {
        "employee": employee.employee_id,
        "updated": employee.updated_at.isoformat(),
        "skills": list(employee.skill_levels.order_by("skill_id").values_list("skill_id", "level")),
        "history": list(
            employee.activities.order_by("id").values_list("event_id", "status", "occurred_at")
        ),
        "engine": ENGINE_VERSION,
    }
    return hashlib.sha256(json.dumps(state, default=str).encode()).hexdigest()


def recommend(
    employee: Employee,
    locale: str = "en",
    limit: int = 3,
    *,
    persist: bool = True,
) -> list[dict]:
    target = next_grade_for(employee)
    if target is None:
        return []
    current = dict(employee.skill_levels.values_list("skill_id", "level"))
    requirements = {
        row.skill_id: row
        for row in GradeRequirement.objects.filter(grade=target).select_related("skill")
    }
    weighted_gap = sum(
        max(row.required_level - current.get(code, 0), 0) * row.priority
        for code, row in requirements.items()
    )
    history = list(
        employee.activities.select_related("event").prefetch_related("event__skill_gains")
    )
    format_completed = Counter(
        item.event.format for item in history if item.status == ActivityHistory.Status.COMPLETED
    )
    format_skipped = Counter(
        item.event.format
        for item in history
        if item.status
        in {
            ActivityHistory.Status.NO_SHOW,
            ActivityHistory.Status.DROPPED,
            ActivityHistory.Status.DECLINED,
        }
    )
    completed_total = sum(format_completed.values())
    skipped_total = sum(format_skipped.values())
    prior_total = completed_total + skipped_total
    candidates: list[Candidate] = []
    for event in _eligible_events(employee):
        impacted = []
        coverage_value = 0
        criticality = 0.0
        gain_value = 0.0
        for gain in event.skill_gains.all():
            requirement = requirements.get(gain.skill_id)
            if requirement is None:
                continue
            level = current.get(gain.skill_id, 0)
            gap = max(requirement.required_level - level, 0)
            actual_gain = max(min(gain.gain, gain.max_level - level, 5 - level), 0)
            useful_gain = min(actual_gain, gap)
            if useful_gain <= 0:
                continue
            coverage_value += useful_gain * requirement.priority
            criticality = max(criticality, min(requirement.priority / 5, 1))
            gain_value += useful_gain / max(gap, 1)
            impacted.append(
                {
                    "skill_code": gain.skill_id,
                    "skill_name": gain.skill.localized_name(locale),
                    "current_level": level,
                    "required_level": requirement.required_level,
                    "gain": actual_gain,
                    "max_level": gain.max_level,
                    "priority": requirement.priority,
                }
            )
        if not impacted:
            continue
        impacted_codes = {item["skill_code"] for item in impacted}
        similar_history = [
            item
            for item in history
            if impacted_codes & {gain.skill_id for gain in item.event.skill_gains.all()}
        ]
        similar_completed = sum(
            item.status == ActivityHistory.Status.COMPLETED for item in similar_history
        )
        similar_skipped = sum(
            item.status
            in {
                ActivityHistory.Status.NO_SHOW,
                ActivityHistory.Status.DROPPED,
                ActivityHistory.Status.DECLINED,
            }
            for item in similar_history
        )
        format_success = format_completed[event.format]
        format_failure = format_skipped[event.format]
        affinity = (format_success + 1) / (format_success + format_failure + 2)
        if prior_total == 0:
            affinity = 0.5
        breakdown = ScoreBreakdown(
            gap_coverage=min(coverage_value / max(weighted_gap, 1), 1),
            criticality=criticality,
            achievable_gain=min(gain_value / len(impacted), 1),
            history_affinity=affinity,
            availability=1.0,
            skip_penalty=min(similar_skipped * 0.04, 0.16),
            repeat_penalty=0.04 if similar_completed >= 2 else 0.0,
        )
        candidates.append(Candidate(event, breakdown, impacted, similar_completed, similar_skipped))
    candidates.sort(key=lambda item: (-item.score.total, item.event.code))

    # Prefer different formats when scores are close, without hiding the best critical-gap option.
    selected: list[Candidate] = []
    used_formats: set[str] = set()
    for candidate in candidates:
        if candidate.event.format not in used_formats or len(selected) == 0:
            selected.append(candidate)
            used_formats.add(candidate.event.format)
        if len(selected) == limit:
            break
    if len(selected) < limit:
        for candidate in candidates:
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) == limit:
                break

    context_hash = _context_hash(employee)
    if persist:
        RecommendationSnapshot.objects.filter(employee=employee).delete()
    response = []
    for rank, candidate in enumerate(selected, start=1):
        primary = max(candidate.impacted_skills, key=lambda item: item["priority"] * item["gain"])
        max_label = "макс." if locale == "ru" else "max"
        history_message = (
            f"Похожие: {candidate.completed_similar} завершено, "
            f"{candidate.skipped_similar} пропущено"
            if locale == "ru"
            else (
                f"Similar: {candidate.completed_similar} completed, "
                f"{candidate.skipped_similar} skipped"
            )
        )
        reasons = [
            {
                "factor": "grade",
                "message": (
                    f"{employee.grade.localized_name(locale)} → {target.localized_name(locale)}"
                ),
            },
            {
                "factor": "skill_gap",
                "message": (
                    f"{primary['skill_name']}: {primary['current_level']} / "
                    f"{primary['required_level']}"
                ),
            },
            {
                "factor": "impact",
                "message": f"+{primary['gain']} ({max_label} {primary['max_level']})",
            },
            {
                "factor": "history",
                "message": history_message,
            },
        ]
        explanation = {
            "summary": (
                f"Закрывает разрыв {primary['skill_name']} для "
                f"грейда {target.localized_name(locale)}"
                if locale == "ru"
                else (f"Closes the {primary['skill_name']} gap for {target.localized_name(locale)}")
            ),
            "reasons": reasons,
            "score_breakdown": {**asdict(candidate.score), "total": candidate.score.total},
            "engine": ENGINE_VERSION,
        }
        snapshot = None
        if persist:
            snapshot = RecommendationSnapshot.objects.create(
                employee=employee,
                event=candidate.event,
                rank=rank,
                score=candidate.score.total,
                explanation=explanation,
                context_hash=context_hash,
            )
        response.append(
            {
                "id": str(snapshot.id) if snapshot else f"preview-{candidate.event.code}",
                "rank": rank,
                "score": candidate.score.total,
                "event": serialize_event(candidate.event, locale),
                "impacted_skills": candidate.impacted_skills,
                "explanation": explanation,
            }
        )
    return response


def serialize_event(event: Event, locale: str = "en") -> dict:
    description = getattr(event, f"description_{locale}", "") or event.description_en
    return {
        "code": event.code,
        "name": event.localized_name(locale),
        "description": description,
        "type": event.event_type,
        "format": event.format,
        "duration_hours": event.duration_hours,
    }
