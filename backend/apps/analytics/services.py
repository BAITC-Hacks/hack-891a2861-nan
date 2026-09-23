from collections import Counter

from django.db.models import Count, Q

from apps.activities.models import ActivityHistory
from apps.catalog.models import GradeRequirement
from apps.employees.models import Employee
from apps.employees.services import next_grade_for
from apps.recommendations.engine import recommend


def dashboard(locale: str = "en") -> dict:
    gap_counts: Counter[str] = Counter()
    gap_names: dict[str, str] = {}
    without_steps = []
    employees = Employee.objects.select_related("role", "grade").prefetch_related("skill_levels")
    for employee in employees:
        target = next_grade_for(employee)
        if target:
            current = dict(employee.skill_levels.values_list("skill_id", "level"))
            for requirement in GradeRequirement.objects.filter(grade=target).select_related(
                "skill"
            ):
                if current.get(requirement.skill_id, 0) < requirement.required_level:
                    gap_counts[requirement.skill_id] += 1
                    gap_names[requirement.skill_id] = requirement.skill.localized_name(locale)
        if not recommend(employee, locale, limit=1, persist=False, use_llm=False):
            without_steps.append(
                {"employee_id": employee.employee_id, "display_name": employee.display_name}
            )

    participation = (
        ActivityHistory.objects.values(
            "event_id", "event__name_en", "event__name_ru", "event__name_kk"
        )
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=ActivityHistory.Status.COMPLETED)),
            missed=Count("id", filter=Q(status=ActivityHistory.Status.MISSED)),
            declined=Count("id", filter=Q(status=ActivityHistory.Status.DECLINED)),
        )
        .order_by("-total")
    )
    return {
        "summary": {
            "employees": employees.count(),
            "completion_rate": _completion_rate(),
            "employees_without_step": len(without_steps),
        },
        "top_skill_gaps": [
            {"skill_code": code, "skill_name": gap_names[code], "employees": count}
            for code, count in gap_counts.most_common(10)
        ],
        "employees_without_step": without_steps,
        "participation": [
            {
                "event_code": item["event_id"],
                "event_name": item[f"event__name_{locale}"] or item["event__name_en"],
                "total": item["total"],
                "completed": item["completed"],
                "missed": item["missed"],
                "declined": item["declined"],
                "completion_rate": round(100 * item["completed"] / item["total"])
                if item["total"]
                else 0,
            }
            for item in participation
        ],
    }


def _completion_rate() -> int:
    total = ActivityHistory.objects.count()
    completed = ActivityHistory.objects.filter(status=ActivityHistory.Status.COMPLETED).count()
    return round(100 * completed / total) if total else 0
