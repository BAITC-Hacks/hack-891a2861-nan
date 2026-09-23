# Архитектурные решения

## ADR-001: Гибридный recommendation engine

**Статус:** accepted.

**Решение:** eligibility, skill arithmetic и base ranking детерминированы; LLM работает поверх top candidates для context-aware reranking и объяснения.

**Почему:** pure rules плохо ловят комбинации факторов, а pure LLM может выбрать несуществующее/недоступное событие. Гибрид даёт explainability, offline fallback и воспроизводимость.

## ADR-002: Модульный монолит

**Статус:** accepted.

**Решение:** Web, API и PostgreSQL — отдельные runtime containers; recommendation engine пока является isolated module API.

**Почему:** 200 employees / 40 events не требуют distributed system. Монолит быстрее собрать, проще тестировать и запускать. Модульная граница оставляет путь к выносу engine при росте.

## ADR-003: PostgreSQL как source of truth

**Статус:** accepted.

**Решение:** импортировать JSON/CSV в normalized relational model; original upload и import report сохранять для audit.

**Почему:** skill updates должны быть атомарными, HR нужны агрегаты, а recommendation audit — воспроизводимым.

## ADR-004: Провайдер-независимый LLM adapter

**Статус:** accepted.

**Решение:** engine зависит от интерфейса structured completion, а endpoint/model/key задаются environment variables.

**Почему:** во время демо можно выбрать cloud или local OpenAI-compatible model, не меняя domain logic.

## ADR-005: Прогресс считает код, не LLM

**Статус:** accepted.

**Решение:** `gain`/`max_level`, grade readiness и HR metrics считаются deterministic domain functions.

**Почему:** это бизнес-правила с точным ожидаемым результатом. LLM не должна быть calculator или source of truth.

## ADR-006: Django + Django REST Framework

**Статус:** accepted.

**Решение:** backend строится на Django и Django REST Framework; Next.js остаётся пользовательским UI, а Django Admin используется для внутреннего управления данными.

**Почему:** домен содержит много связанных сущностей, permissions, migrations, transactional updates и imports. Django снижает hackathon risk за счёт готовых ORM, auth и admin. Recommendation engine остаётся framework-independent Python module и может быть вынесен позже.
