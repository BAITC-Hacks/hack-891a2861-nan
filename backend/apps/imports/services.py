import csv
import io
import json
from datetime import datetime
from typing import BinaryIO

from django.db import transaction
from django.utils import timezone

from apps.activities.models import ActivityHistory
from apps.catalog.models import Event, EventSkillGain, Grade, GradeRequirement, Role, Skill
from apps.employees.models import Employee, EmployeeSkill


class DatasetValidationError(ValueError):
    def __init__(self, errors: list[dict]):
        super().__init__("Dataset validation failed")
        self.errors = errors


def _json_document(file: BinaryIO, label: str) -> dict:
    try:
        file.seek(0)
        payload = json.load(file)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DatasetValidationError([{"file": label, "message": str(exc)}]) from exc
    if isinstance(payload, list):
        return {label.removesuffix(".json"): payload}
    if not isinstance(payload, dict):
        raise DatasetValidationError([{"file": label, "message": "Expected a JSON object"}])
    return payload


def _translations(item: dict, field: str = "name") -> dict:
    value = item.get(field, item.get("title", ""))
    if isinstance(value, str):
        value = {"en": value}
    return {
        f"{field}_en": value.get("en", item.get(f"{field}_en", "")),
        f"{field}_ru": value.get("ru", item.get(f"{field}_ru", "")),
        f"{field}_kk": value.get("kk", item.get(f"{field}_kk", "")),
    }


@transaction.atomic
def import_dataset(*, employees_file, skills_file, events_file, history_file) -> dict:
    employee_doc = _json_document(employees_file, "employees.json")
    skill_doc = _json_document(skills_file, "skills.json")
    event_doc = _json_document(events_file, "events.json")
    employees = employee_doc.get("employees", [])
    skills = skill_doc.get("skills", [])
    role_profiles = skill_doc.get("role_profiles", [])
    events = event_doc.get("events", [])
    try:
        history_file.seek(0)
        history = list(csv.DictReader(io.TextIOWrapper(history_file, encoding="utf-8-sig")))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise DatasetValidationError(
            [{"file": "activity_history.csv", "message": str(exc)}]
        ) from exc

    errors: list[dict] = []
    counts = {
        "skills": 0,
        "role_profiles": 0,
        "employees": 0,
        "events": 0,
        "history": 0,
    }
    grade_ranks = {"junior": 1, "middle": 2, "senior": 3, "lead": 4}

    for index, item in enumerate(skills):
        try:
            code = str(item["skill_id"])
            Skill.objects.update_or_create(
                code=code,
                defaults={
                    **_translations(item),
                    "kind": item.get("type", Skill.Kind.HARD),
                    "description_en": item.get("description", ""),
                },
            )
            counts["skills"] += 1
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"file": "skills.json", "index": index, "message": str(exc)})

    for index, profile in enumerate(role_profiles):
        try:
            role_name = str(profile["role"])
            grade_name = str(profile["grade"])
            role, _ = Role.objects.get_or_create(
                code=_slug(role_name), defaults={"name_en": role_name}
            )
            grade, _ = Grade.objects.update_or_create(
                role=role,
                code=_slug(grade_name),
                defaults={
                    "name_en": grade_name,
                    "rank": grade_ranks[grade_name.lower()],
                },
            )
            critical = set(profile.get("critical_skills", []))
            for skill_code, required_level in profile.get("required_skills", {}).items():
                GradeRequirement.objects.update_or_create(
                    grade=grade,
                    skill=Skill.objects.get(pk=skill_code),
                    defaults={
                        "required_level": int(required_level),
                        "priority": 5 if skill_code in critical else 3,
                    },
                )
            counts["role_profiles"] += 1
        except (KeyError, TypeError, ValueError, Skill.DoesNotExist) as exc:
            errors.append(
                {"file": "skills.json", "section": "role_profiles", "index": index, "message": str(exc)}
            )

    for index, item in enumerate(employees):
        try:
            role = Role.objects.get(pk=_slug(item["role"]))
            grade = Grade.objects.get(role=role, code=_slug(item["grade"]))
            employee, _ = Employee.objects.update_or_create(
                employee_id=str(item["employee_id"]),
                defaults={
                    "display_name": item.get("full_name", item["employee_id"]),
                    "role": role,
                    "grade": grade,
                    "tenure_months": int(item.get("tenure_months", 0)),
                    "organisation_unit": item.get("department", ""),
                    "manager_id": item.get("manager_id"),
                    "hire_date": item.get("hire_date") or None,
                    "work_format": item.get("work_format", ""),
                    "locale": item.get("preferred_language", "ru"),
                    "career_goal": item.get("career_goal"),
                    "last_review_date": item.get("last_review_date") or None,
                },
            )
            seen_skills = set()
            for skill_code, level in item.get("skills", {}).items():
                EmployeeSkill.objects.update_or_create(
                    employee=employee,
                    skill=Skill.objects.get(pk=skill_code),
                    defaults={"level": int(level)},
                )
                seen_skills.add(skill_code)
            employee.skill_levels.exclude(skill_id__in=seen_skills).delete()
            counts["employees"] += 1
        except (KeyError, TypeError, ValueError, Role.DoesNotExist, Grade.DoesNotExist, Skill.DoesNotExist) as exc:
            errors.append({"file": "employees.json", "index": index, "message": str(exc)})

    for index, item in enumerate(events):
        try:
            event, _ = Event.objects.update_or_create(
                code=str(item["event_id"]),
                defaults={
                    **_translations(item),
                    **_translations(item, "description"),
                    "event_type": item.get("type", "course"),
                    "format": item.get("format", Event.Format.ONLINE),
                    "duration_hours": max(1, round(float(item.get("duration_hours", 1)))),
                    "is_active": True,
                    "is_mandatory": bool(item.get("mandatory", False)),
                    "repeatable": item.get("event_id") == "EV_036",
                    "prerequisites": item.get("prerequisites", {}),
                    "upcoming_sessions": item.get("upcoming_sessions", []),
                },
            )
            target_role_codes = [_slug(name) for name in item.get("target_roles", [])]
            target_roles = Role.objects.filter(code__in=target_role_codes)
            event.audience_roles.set(target_roles)
            event.audience_grades.set(
                Grade.objects.filter(
                    role__in=target_roles,
                    code__in=[_slug(name) for name in item.get("target_grades", [])],
                )
            )
            seen_gains = set()
            for gain in item.get("develops_skills", []):
                skill_code = gain["skill_id"]
                EventSkillGain.objects.update_or_create(
                    event=event,
                    skill=Skill.objects.get(pk=skill_code),
                    defaults={
                        "gain": int(gain.get("gain", 1)),
                        "max_level": int(gain.get("max_level", 5)),
                    },
                )
                seen_gains.add(skill_code)
            event.skill_gains.exclude(skill_id__in=seen_gains).delete()
            counts["events"] += 1
        except (KeyError, TypeError, ValueError, Skill.DoesNotExist) as exc:
            errors.append({"file": "events.json", "index": index, "message": str(exc)})

    valid_statuses = {choice for choice, _ in ActivityHistory.Status.choices}
    for index, item in enumerate(history, start=2):
        try:
            status = item["status"].strip().lower()
            if status not in valid_statuses:
                raise ValueError(f"Unknown status {status}")
            occurred = datetime.fromisoformat(item.get("date") or item["occurred_at"])
            if timezone.is_naive(occurred):
                occurred = timezone.make_aware(occurred)
            due_date = item.get("due_date")
            completed_on_time = None
            if status == ActivityHistory.Status.COMPLETED and due_date:
                completed_on_time = occurred.date() <= datetime.fromisoformat(due_date).date()
            defaults = {
                "employee": Employee.objects.get(pk=item["employee_id"]),
                "event": Event.objects.get(pk=item["event_id"]),
                "status": status,
                "occurred_at": occurred,
                "completed_on_time": completed_on_time,
                "completion_pct": int(item.get("completion_pct") or 0),
                "score": _optional_int(item.get("score")),
                "feedback_rating": _optional_int(item.get("feedback_rating")),
                "assigned_by": item.get("assigned_by", ""),
                "source": "dataset",
            }
            record_id = item.get("record_id")
            if record_id:
                ActivityHistory.objects.update_or_create(external_id=record_id, defaults=defaults)
            else:
                ActivityHistory.objects.update_or_create(
                    employee=defaults["employee"],
                    event=defaults["event"],
                    occurred_at=occurred,
                    defaults=defaults,
                )
            counts["history"] += 1
        except (KeyError, TypeError, ValueError, Employee.DoesNotExist, Event.DoesNotExist) as exc:
            errors.append({"file": "activity_history.csv", "row": index, "message": str(exc)})

    if errors:
        transaction.set_rollback(True)
        raise DatasetValidationError(errors[:100])
    return counts


def _slug(value: str) -> str:
    return "_".join(value.lower().strip().replace("/", " ").split())


def _optional_int(value: str | None) -> int | None:
    return int(value) if value not in {None, ""} else None
