# Career Quest

Explainable AI navigator for employee development, built for the Halyk Bank track at HackAlem AI.

Career Quest shows an employee their next-grade trajectory, selects 1–3 relevant development activities from profile, skill gaps and participation history, explains every choice with evidence, and updates progress after completion. HR receives an aggregated capability and participation view without public employee rankings.

> Русская версия описания находится [ниже](#о-проекте).

## Run the complete application

Requirements: Docker with Compose support.

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Web application: http://localhost:3000
- API documentation: http://localhost:8000/api/docs/
- Django Admin: http://localhost:8000/admin/

Demo Admin credentials are `admin` / `careerquest-demo`. They exist only in the synthetic demo seed and must not be used in a real deployment.

The first launch applies migrations and loads a small synthetic demonstration dataset. Later launches preserve PostgreSQL data and do not reset completed activities.

LLM credentials are optional. Without them, the evidence-grounded deterministic decision engine provides the complete MVP flow. To enable multilingual LLM-enhanced explanations, configure an OpenAI-compatible provider in `.env`:

```dotenv
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=...
LLM_MODEL=...
```

## Demonstration flow

1. Open employee `E0028`.
2. Review the Middle → Senior trajectory and skill gaps.
3. Inspect the top recommendation and its grade, gap, impact and history evidence.
4. Notice that Public Speaking is the lowest skill but is penalised after three similar skips; critical System Design work ranks higher.
5. Complete an activity and observe the skill level and readiness update.
6. Open HR Overview to inspect common gaps, recommendation coverage and activity participation.
7. Open Import Data to upload additional judge profiles in the starter-kit-compatible format.

## Implemented MVP requirements

| Requirement | Implementation |
|---|---|
| Profile and trajectory | Arbitrary employee selection, skills, current/target grade, gaps, history and readiness |
| 1–3 recommendations | Eligibility, multi-factor scoring, diversity selection and optional LLM explanation |
| Explainability | Grade, next-grade gap, achievable gain and participation-history evidence plus score breakdown |
| Progress update | Transactional, idempotent `gain/max_level` application and immediate trajectory refresh |
| HR view | Frequent skill gaps, employees without a step, participation and completion rates |
| Judge profiles | Atomic multipart import of employees, skills, events and history |
| Privacy/security | Employee/HR policy boundary, scoped APIs, minimised LLM payload, no public rankings |
| Reproducibility | Docker Compose, migrations, deterministic demo seed, tests and OpenAPI |

## Recommendation approach

The engine is hybrid and bounded:

```text
validated data
  → hard eligibility filters
  → next-grade gap features
  → multi-factor deterministic score
  → diversity selection
  → optional LLM explanation of supplied facts
  → schema/evidence validation or deterministic fallback
```

Base score:

```text
0.40 gap coverage
+ 0.20 critical skill priority
+ 0.15 achievable gain
+ 0.15 participation affinity
+ 0.10 availability
- skip-pattern penalty
- repetition penalty
```

An LLM never creates an activity, changes a skill level, or performs progress arithmetic. It receives no employee name or identifier and may only phrase the supplied evidence. Timeout, invalid JSON or an unsupported claim activates the deterministic fallback.

## Repository

```text
backend/       Django, DRF, recommendation engine, imports and tests
frontend/      Next.js bilingual employee and HR application
docs/          architecture, system design, decisions and dataset contract
compose.yaml   PostgreSQL + backend + frontend one-command runtime
```

Key documentation:

- [High-Level System Design](docs/SYSTEM_DESIGN.md)
- [Detailed Architecture](docs/ARCHITECTURE.md)
- [Architecture Decisions](docs/DECISIONS.md)
- [Dataset Contract](docs/DATASET.md)
- [Backend Guide](backend/README.md)
- [Frontend Guide](frontend/README.md)

## Local development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python manage.py migrate
python manage.py seed_demo --if-empty
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Verification:

```bash
cd backend && pytest && ruff check . && python manage.py check
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```

## Production note

`DJANGO_DEMO_MODE=true` is intentionally enabled in Compose for jury access. A real deployment must set it to `false`, connect corporate OIDC/JWT authentication and enforce HR organisational scopes. The custom user model and server-side permission boundary are already prepared for that integration.

---

## О проекте

Career Quest — AI-навигатор развития сотрудника для трека Halyk Bank на HackAlem AI.

Система показывает траекторию к следующему грейду, находит 1–3 релевантные активности по профилю, разрывам в навыках и истории участия, объясняет выбор проверяемыми фактами и пересчитывает прогресс после выполнения.

### Запуск

```bash
cp .env.example .env
docker compose up --build
```

После запуска:

- интерфейс: http://localhost:3000
- Swagger/OpenAPI: http://localhost:8000/api/docs/
- Django Admin: http://localhost:8000/admin/

Демоданные создаются при первом запуске и не перезаписываются при повторном. LLM-ключ не обязателен: без него полный core flow работает на детерминированном explainable engine.

### Что показать жюри

1. Открыть `E0028`.
2. Показать траекторию Middle → Senior.
3. Раскрыть «Почему этот шаг»: грейд, gap, эффект и история.
4. Обратить внимание: Public Speaking ниже всего, но после трёх пропусков и при критичном System Design он не становится top-1.
5. Завершить активность и показать новые skill level и readiness.
6. Открыть HR-экран и импорт проверочных профилей.

### Ключевое решение

LLM не является source of truth. Допустимость события, skill arithmetic и base score считаются кодом. LLM может только сформулировать объяснение из переданных фактов. Это даёт проверяемость, privacy и fallback при сбое внешней модели.
