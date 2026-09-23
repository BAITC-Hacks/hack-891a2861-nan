from django.db import transaction
from django.utils import timezone

from apps.activities.models import ActivityHistory, SkillChangeLog
from apps.catalog.models import Event
from apps.employees.models import Employee, EmployeeSkill
from apps.employees.services import trajectory_for


@transaction.atomic
def complete_activity(employee: Employee, event: Event, idempotency_key: str) -> dict:
    existing = ActivityHistory.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.employee_id != employee.employee_id or existing.event_id != event.code:
            raise ValueError("Idempotency key is already used for a different completion")
        return _completion_result(existing, employee)

    if (
        not event.repeatable
        and ActivityHistory.objects.filter(
            employee=employee, event=event, status=ActivityHistory.Status.COMPLETED
        ).exists()
    ):
        raise ValueError("This activity has already been completed")

    activity = ActivityHistory.objects.create(
        employee=employee,
        event=event,
        status=ActivityHistory.Status.COMPLETED,
        occurred_at=timezone.now(),
        completed_on_time=True,
        idempotency_key=idempotency_key,
        source="application",
    )
    for rule in event.skill_gains.select_related("skill"):
        employee_skill, _ = EmployeeSkill.objects.select_for_update().get_or_create(
            employee=employee,
            skill=rule.skill,
            defaults={"level": 0},
        )
        before = employee_skill.level
        after = min(before + rule.gain, rule.max_level, 5)
        employee_skill.level = after
        employee_skill.save(update_fields=["level", "updated_at"])
        SkillChangeLog.objects.create(
            activity=activity,
            skill=rule.skill,
            before_level=before,
            after_level=after,
        )
    Employee.objects.filter(pk=employee.pk).update(updated_at=timezone.now())
    employee.refresh_from_db()
    return _completion_result(activity, employee)


def _completion_result(activity: ActivityHistory, employee: Employee) -> dict:
    changes = activity.skill_changes.select_related("skill")
    return {
        "activity_id": str(activity.id),
        "event_code": activity.event_id,
        "status": activity.status,
        "skill_changes": [
            {
                "skill_code": change.skill_id,
                "skill_name": change.skill.name_en,
                "before": change.before_level,
                "after": change.after_level,
            }
            for change in changes
        ],
        "trajectory": trajectory_for(employee, employee.locale),
    }
