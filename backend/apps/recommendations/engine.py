from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date

from django.db.models import Prefetch

from apps.activities.models import ActivityHistory
from apps.catalog.models import Event, EventSkillGain, GradeRequirement
from apps.employees.models import Employee
from apps.employees.services import next_grade_for
from apps.recommendations.completion import predict_completion_probabilities
from apps.recommendations.explainer import explain_recommendations, recommendation_evidence
from apps.recommendations.models import RecommendationSnapshot
from apps.recommendations.scoring import ScoreBreakdown

ENGINE_VERSION = "hybrid-ml-v2"


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
    goal = employee.career_goal or {}
    allowed_roles = {employee.role.name_en, goal.get("target_role")}
    allowed_grades = {employee.grade.name_en, goal.get("target_grade")}
    eligible = []
    for event in queryset:
        if event.available_from and event.available_from > today:
            continue
        if event.available_until and event.available_until < today:
            continue
        role_ids = {role.code for role in event.audience_roles.all()}
        grade_ids = {grade.id for grade in event.audience_grades.all()}
        role_names = {role.name_en for role in event.audience_roles.all()}
        grade_names = {grade.name_en for grade in event.audience_grades.all()}
        if role_ids and not role_names.intersection(allowed_roles):
            continue
        if grade_ids and not grade_names.intersection(allowed_grades):
            continue
        if event.code in completed_ids and not event.repeatable:
            continue
        levels = dict(employee.skill_levels.values_list("skill_id", "level"))
        if any(levels.get(code, 0) < level for code, level in event.prerequisites.items()):
            continue
        eligible.append(event)
    return eligible


def recommend(
    employee: Employee,
    locale: str = "en",
    limit: int = 3,
    *,
    persist: bool = True,
    use_llm: bool = True,
    use_ml: bool = True,
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
    eligible_events = _eligible_events(employee)
    completion_probabilities = (
        predict_completion_probabilities(employee, eligible_events, history)
        if use_ml
        else {}
    )
    focus_skills = set((employee.career_goal or {}).get("focus_skills", []))
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
    for event in eligible_events:
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
            priority = min(requirement.priority / 5, 1)
            if gain.skill_id in focus_skills:
                priority = 1.0
            criticality = max(criticality, priority)
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
            completion_probability=completion_probabilities.get(event.code, 0.5),
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

    response = []
    for rank, candidate in enumerate(selected, start=1):
        primary = max(candidate.impacted_skills, key=lambda item: item["priority"] * item["gain"])
        max_label = {"ru": "макс.", "kk": "макс.", "en": "max"}.get(locale, "max")
        history_message = _history_message(
            locale, candidate.completed_similar, candidate.skipped_similar
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
            {
                "factor": "completion_probability",
                "message": f"{candidate.score.completion_probability:.0%}",
            },
        ]
        explanation = {
            "summary": _summary(locale, primary["skill_name"], target.localized_name(locale)),
            "reasons": reasons,
            "score_breakdown": {**asdict(candidate.score), "total": candidate.score.total},
            "engine": ENGINE_VERSION,
        }
        response.append(
            {
                "id": f"preview-{candidate.event.code}",
                "rank": rank,
                "score": candidate.score.total,
                "event": serialize_event(candidate.event, locale),
                "impacted_skills": candidate.impacted_skills,
                "explanation": explanation,
                "evidence": {
                    "grade": reasons[0]["message"],
                    "skill_gaps": candidate.impacted_skills,
                    "impact": reasons[2]["message"],
                    "history": {
                        "similar_completed": candidate.completed_similar,
                        "similar_not_completed": candidate.skipped_similar,
                    },
                    "completion_probability": candidate.score.completion_probability,
                },
            }
        )

    _, evidence_hash = recommendation_evidence(employee, target, response, locale)
    context_hash = evidence_hash
    cached = list(
        RecommendationSnapshot.objects.filter(
            employee=employee,
            context_hash=context_hash,
            engine_version=ENGINE_VERSION,
        ).select_related("event")
    ) if persist and use_llm else []
    if len(cached) == len(response) and [row.event_id for row in cached] == [
        item["event"]["code"] for item in response
    ]:
        for item, snapshot in zip(response, cached, strict=True):
            item["id"] = str(snapshot.id)
            item["explanation"] = snapshot.explanation
            item.pop("evidence", None)
        return response

    explained = (
        explain_recommendations(employee, target, response, locale)
        if use_llm
        else None
    )
    if explained:
        for item, explanation in zip(response, explained.explanations, strict=True):
            item["explanation"] = {
                **explanation,
                "ai_source": explained.source,
                "ai_latency_ms": explained.latency_ms,
            }
    if persist:
        RecommendationSnapshot.objects.filter(employee=employee).delete()
        for item, candidate in zip(response, selected, strict=True):
            snapshot = RecommendationSnapshot.objects.create(
                employee=employee,
                event=candidate.event,
                rank=item["rank"],
                score=item["score"],
                explanation=item["explanation"],
                engine_version=ENGINE_VERSION,
                context_hash=context_hash,
            )
            item["id"] = str(snapshot.id)
    for item in response:
        item.pop("evidence", None)
    return response


def _history_message(locale: str, completed: int, not_completed: int) -> str:
    if locale == "ru":
        return f"Похожие активности: {completed} завершено, {not_completed} не завершено"
    if locale == "kk":
        return f"Ұқсас белсенділіктер: {completed} аяқталды, {not_completed} аяқталмады"
    return f"Similar activities: {completed} completed, {not_completed} not completed"


def _summary(locale: str, skill: str, grade: str) -> str:
    if locale == "ru":
        return (
            f"Эта активность поможет вам приблизиться к грейду {grade}, потому что развивает "
            f"навык {skill}, по которому сейчас есть разрыв с требованиями следующего уровня. "
            "Её эффект рассчитан по текущему уровню, приросту активности и максимально "
            "допустимому уровню. История похожих активностей и вероятность завершения также "
            "учтены в рейтинге, поэтому это не просто выбор самого низкого навыка."
        )
    if locale == "kk":
        return (
            f"Бұл белсенділік {grade} деңгейіне жақындауға көмектеседі, себебі ол талаптармен "
            f"алшақтық бар {skill} дағдысын дамытады. Әсер ағымдағы деңгей, белсенділіктің "
            "өсімі және ең жоғары рұқсат етілген деңгей бойынша есептелді. Ұқсас "
            "белсенділіктер тарихы мен аяқтау ықтималдығы да рейтингте ескерілді, сондықтан "
            "ұсыныс тек ең төмен дағдыға негізделмейді."
        )
    return (
        f"This activity helps you move toward the {grade} grade because it develops {skill}, "
        "where your current level is below the target requirement. Its impact is calculated "
        "from your current level, the activity gain, and its maximum allowed level. Your "
        "history with similar activities and predicted likelihood of completion also influence "
        "its position, so this is not simply a recommendation of your lowest-rated skill."
    )


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
