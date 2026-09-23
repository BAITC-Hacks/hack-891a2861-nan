from dataclasses import asdict, dataclass

from apps.catalog.models import Grade, GradeRequirement
from apps.employees.models import Employee


@dataclass(frozen=True)
class SkillGap:
    skill_code: str
    skill_name: str
    kind: str
    current_level: int
    required_level: int
    gap: int
    priority: int


def next_grade_for(employee: Employee) -> Grade | None:
    goal = employee.career_goal or {}
    target_role = goal.get("target_role")
    target_grade = goal.get("target_grade")
    if target_role and target_grade:
        goal_grade = Grade.objects.filter(
            role__name_en=target_role,
            name_en=target_grade,
        ).first()
        if goal_grade:
            return goal_grade
    return (
        Grade.objects.filter(role=employee.role, rank__gt=employee.grade.rank)
        .order_by("rank")
        .first()
    )


def trajectory_for(employee: Employee, locale: str = "en") -> dict:
    target = next_grade_for(employee)
    current_levels = {
        item.skill_id: item.level for item in employee.skill_levels.select_related("skill").all()
    }
    requirements = []
    gaps: list[SkillGap] = []
    if target:
        requirements = GradeRequirement.objects.filter(grade=target).select_related("skill")
        for requirement in requirements:
            current = current_levels.get(requirement.skill_id, 0)
            gaps.append(
                SkillGap(
                    skill_code=requirement.skill_id,
                    skill_name=requirement.skill.localized_name(locale),
                    kind=requirement.skill.kind,
                    current_level=current,
                    required_level=requirement.required_level,
                    gap=max(requirement.required_level - current, 0),
                    priority=requirement.priority,
                )
            )
    total_required = sum(item.required_level for item in requirements)
    achieved = sum(
        min(current_levels.get(item.skill_id, 0), item.required_level) for item in requirements
    )
    readiness = round(100 * achieved / total_required) if total_required else 100
    gaps.sort(key=lambda gap: (-gap.priority, -gap.gap, gap.skill_code))
    return {
        "current_grade": {
            "code": employee.grade.code,
            "name": employee.grade.localized_name(locale),
            "rank": employee.grade.rank,
        },
        "target_grade": (
            {"code": target.code, "name": target.localized_name(locale), "rank": target.rank}
            if target
            else None
        ),
        "readiness_percent": readiness,
        "gaps": [asdict(gap) for gap in gaps],
        "is_top_grade": target is None,
    }
