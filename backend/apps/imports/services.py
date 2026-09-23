import csv
import io
import json
from datetime import datetime
from typing import BinaryIO

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.activities.models import ActivityHistory
from apps.catalog.models import Event, EventSkillGain, Grade, GradeRequirement, Role, Skill
from apps.employees.models import Employee, EmployeeSkill


class DatasetValidationError(ValueError):
    def __init__(self, errors: list[dict]):
        super().__init__("Dataset validation failed")
        self.errors = errors


def _json_data(file: BinaryIO, label: str) -> list[dict]:
    try:
        payload = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DatasetValidationError([{"file": label, "message": str(exc)}]) from exc
    if isinstance(payload, dict):
        payload = payload.get(label.removesuffix(".json"), payload.get("data", payload))
    if not isinstance(payload, list):
        raise DatasetValidationError([{"file": label, "message": "Expected a JSON array"}])
    return payload


def _value(item: dict, *keys, required: bool = True, default=None):
    for key in keys:
        if key in item:
            return item[key]
    if required:
        raise KeyError(keys[0])
    return default


def _translations(item: dict, field: str = "name") -> dict:
    value = item.get(field, {})
    if isinstance(value, str):
        value = {"en": value}
    return {
        f"{field}_en": value.get("en", item.get(f"{field}_en", item.get("title", ""))),
        f"{field}_ru": value.get("ru", item.get(f"{field}_ru", "")),
        f"{field}_kk": value.get("kk", item.get(f"{field}_kk", "")),
    }


@transaction.atomic
def import_dataset(*, employees_file, skills_file, events_file, history_file) -> dict:
    employees = _json_data(employees_file, "employees.json")
    skills = _json_data(skills_file, "skills.json")
    events = _json_data(events_file, "events.json")
    try:
        history_file.seek(0)
        history_text = io.TextIOWrapper(history_file, encoding="utf-8-sig")
        history = list(csv.DictReader(history_text))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise DatasetValidationError(
            [{"file": "activity_history.csv", "message": str(exc)}]
        ) from exc

    errors: list[dict] = []
    counts = {"skills": 0, "employees": 0, "events": 0, "history": 0}
    grade_ranks = {"intern": 0, "junior": 1, "middle": 2, "senior": 3, "lead": 4}

    for index, item in enumerate(skills):
        try:
            code = str(_value(item, "skill_id", "code", "id"))
            skill, _ = Skill.objects.update_or_create(
                code=code,
                defaults={
                    **_translations(item),
                    "kind": item.get("type", item.get("kind", Skill.Kind.HARD)),
                },
            )
            for requirement in item.get("requirements", []):
                role_name = str(_value(requirement, "role"))
                grade_name = str(_value(requirement, "grade"))
                role, _ = Role.objects.get_or_create(
                    code=_slug(role_name), defaults={"name_en": role_name}
                )
                grade, _ = Grade.objects.get_or_create(
                    role=role,
                    code=_slug(grade_name),
                    defaults={
                        "name_en": grade_name,
                        "rank": requirement.get(
                            "rank", grade_ranks.get(grade_name.lower(), role.grades.count())
                        ),
                    },
                )
                GradeRequirement.objects.update_or_create(
                    grade=grade,
                    skill=skill,
                    defaults={
                        "required_level": int(_value(requirement, "level", "required_level")),
                        "priority": int(requirement.get("priority", 3)),
                    },
                )
            counts["skills"] += 1
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"file": "skills.json", "index": index, "message": str(exc)})

    for index, item in enumerate(employees):
        try:
            role_name = str(_value(item, "role"))
            grade_name = str(_value(item, "grade"))
            role, _ = Role.objects.get_or_create(
                code=_slug(role_name), defaults={"name_en": role_name}
            )
            grade, _ = Grade.objects.get_or_create(
                role=role,
                code=_slug(grade_name),
                defaults={
                    "name_en": grade_name,
                    "rank": item.get(
                        "grade_rank", grade_ranks.get(grade_name.lower(), role.grades.count())
                    ),
                },
            )
            employee_id = str(_value(item, "employee_id", "id"))
            employee, _ = Employee.objects.update_or_create(
                employee_id=employee_id,
                defaults={
                    "display_name": item.get("display_name", item.get("name", employee_id)),
                    "role": role,
                    "grade": grade,
                    "tenure_months": int(item.get("tenure_months", item.get("tenure", 0))),
                    "organisation_unit": item.get("organisation_unit", item.get("department", "")),
                    "locale": item.get("locale", "ru"),
                },
            )
            for skill_code, level in item.get("skills", {}).items():
                try:
                    skill = Skill.objects.get(pk=skill_code)
                except Skill.DoesNotExist:
                    errors.append(
                        {
                            "file": "employees.json",
                            "index": index,
                            "message": f"Unknown skill {skill_code}",
                        }
                    )
                    continue
                EmployeeSkill.objects.update_or_create(
                    employee=employee, skill=skill, defaults={"level": int(level)}
                )
            counts["employees"] += 1
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"file": "employees.json", "index": index, "message": str(exc)})

    for index, item in enumerate(events):
        try:
            code = str(_value(item, "event_id", "code", "id"))
            event, _ = Event.objects.update_or_create(
                code=code,
                defaults={
                    **_translations(item),
                    **_translations(item, "description"),
                    "event_type": item.get("type", "learning"),
                    "format": item.get("format", Event.Format.COURSE),
                    "duration_hours": int(item.get("duration_hours", 1)),
                    "is_active": item.get("is_active", True),
                    "is_mandatory": item.get("is_mandatory", False),
                    "repeatable": item.get("repeatable", False),
                },
            )
            audience = item.get("audience", {})
            if isinstance(audience, dict):
                event.audience_roles.set(
                    Role.objects.filter(code__in=[_slug(x) for x in audience.get("roles", [])])
                )
            gains = item.get("skills", item.get("skill_gains", []))
            for gain in gains:
                skill_code = str(_value(gain, "skill_id", "skill", "code"))
                skill = Skill.objects.get(pk=skill_code)
                EventSkillGain.objects.update_or_create(
                    event=event,
                    skill=skill,
                    defaults={
                        "gain": int(gain.get("gain", 1)),
                        "max_level": int(gain.get("max_level", 5)),
                    },
                )
            counts["events"] += 1
        except (KeyError, TypeError, ValueError, Skill.DoesNotExist) as exc:
            errors.append({"file": "events.json", "index": index, "message": str(exc)})

    valid_statuses = {choice for choice, _ in ActivityHistory.Status.choices}
    for index, item in enumerate(history, start=2):
        try:
            status = item["status"].strip().lower()
            if status not in valid_statuses:
                raise ValueError(f"Unknown status {status}")
            occurred = parse_datetime(item.get("occurred_at", ""))
            if occurred is None:
                occurred = datetime.fromisoformat(item["occurred_at"])
                if timezone.is_naive(occurred):
                    occurred = timezone.make_aware(occurred)
            ActivityHistory.objects.update_or_create(
                employee=Employee.objects.get(pk=item["employee_id"]),
                event=Event.objects.get(pk=item["event_id"]),
                occurred_at=occurred,
                defaults={
                    "status": status,
                    "completed_on_time": _optional_bool(item.get("completed_on_time")),
                    "source": "dataset",
                },
            )
            counts["history"] += 1
        except (KeyError, TypeError, ValueError, Employee.DoesNotExist, Event.DoesNotExist) as exc:
            errors.append({"file": "activity_history.csv", "row": index, "message": str(exc)})

    if errors:
        transaction.set_rollback(True)
        raise DatasetValidationError(errors)
    return counts


def _slug(value: str) -> str:
    return "_".join(value.lower().strip().replace("/", " ").split())


def _optional_bool(value: str | None) -> bool | None:
    if value is None or str(value).strip() == "":
        return None
    return str(value).lower() in {"1", "true", "yes"}
