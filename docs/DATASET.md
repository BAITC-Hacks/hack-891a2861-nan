# Dataset contract

The importer accepts four multipart fields: `employees`, `skills`, `events` and `history`. Maximum file size is 10 MB each. The complete import runs in one database transaction; any validation error rolls it back.

This contract is based on the task description and intentionally accepts common aliases such as `id`/`employee_id` and `code`/`skill_id`. When the official starter-kit README is delivered, an adapter can be added inside `apps/imports` without changing the domain model.

## employees.json

```json
[
  {
    "employee_id": "E0028",
    "display_name": "Synthetic Employee 28",
    "role": "Backend Engineer",
    "grade": "Middle",
    "grade_rank": 2,
    "tenure_months": 52,
    "department": "Digital Channels",
    "locale": "ru",
    "skills": {
      "SK_PYTHON": 3,
      "SK_SYSTEM_DESIGN": 2
    }
  }
]
```

Skill levels must be integers from 0 to 5 and must reference skills from `skills.json`.

## skills.json

```json
[
  {
    "skill_id": "SK_SYSTEM_DESIGN",
    "type": "hard",
    "name": {
      "en": "System Design",
      "ru": "Системный дизайн",
      "kk": "Жүйелік дизайн"
    },
    "requirements": [
      {
        "role": "Backend Engineer",
        "grade": "Senior",
        "rank": 3,
        "level": 4,
        "priority": 5
      }
    ]
  }
]
```

## events.json

```json
[
  {
    "event_id": "EV_SYSTEM_DESIGN",
    "name": {
      "en": "System Design Lab",
      "ru": "Лаборатория System Design",
      "kk": "System Design зертханасы"
    },
    "description": {
      "en": "Architecture workshop",
      "ru": "Архитектурный практикум"
    },
    "type": "development",
    "format": "workshop",
    "duration_hours": 8,
    "is_mandatory": false,
    "repeatable": false,
    "audience": {
      "roles": ["Backend Engineer"]
    },
    "skills": [
      {
        "skill_id": "SK_SYSTEM_DESIGN",
        "gain": 1,
        "max_level": 5
      }
    ]
  }
]
```

Supported formats: `course`, `workshop`, `mentoring`, `project`, `assessment`.

## activity_history.csv

```csv
employee_id,event_id,status,occurred_at,completed_on_time
E0028,EV_SYSTEM_DESIGN,completed,2026-05-14T09:00:00+05:00,true
E0028,EV_SPEAKING,missed,2026-06-01T09:00:00+05:00,false
```

Supported statuses: `registered`, `completed`, `missed`, `declined`.

## Error response

Errors identify their source file and JSON index or CSV row:

```json
{
  "error": {
    "code": "invalid_dataset",
    "details": [
      {
        "file": "employees.json",
        "index": 0,
        "message": "Unknown skill SK_UNKNOWN"
      }
    ]
  }
}
```
