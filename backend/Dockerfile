FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml ./
COPY apps ./apps
COPY config ./config
COPY manage.py ./
RUN pip install .
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

USER app
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_demo --if-empty && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 30"]
