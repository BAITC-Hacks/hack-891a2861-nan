# Career Quest Backend

Django REST Framework backend for Career Quest.

## Local development

Python 3.12+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

The development configuration uses SQLite unless PostgreSQL environment variables are supplied. PostgreSQL is the target runtime database.

Useful endpoints:

- `GET /api/v1/health/live/`
- `GET /api/v1/health/ready/`
- `GET /api/v1/meta/`
- `GET /api/schema/`
- `GET /api/docs/`
- `/admin/`

Run checks and tests:

```bash
python manage.py check
pytest
ruff check .
```

## Modules

```text
apps/
├── accounts/          # identity, roles and organisation scope
├── employees/         # profiles, employee skills and trajectory
├── catalog/           # skills, grades, events and gains
├── activities/        # participation and progress updates
├── recommendations/   # scoring, LLM adapter and evidence
├── analytics/         # HR aggregates
└── imports/           # JSON/CSV validation and ingestion
```

Business logic belongs in application/domain services, not in API views. Infrastructure integrations are accessed through explicit adapters.
