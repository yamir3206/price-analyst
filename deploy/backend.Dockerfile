FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend/src

WORKDIR /app

COPY backend/pyproject.toml backend/README.md /app/backend/
COPY backend/src /app/backend/src
COPY backend/migrations /app/backend/migrations
COPY backend/alembic.ini /app/backend/alembic.ini

RUN python -m pip install --no-cache-dir /app/backend \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && mkdir --parents /data \
    && chown --recursive appuser:appuser /app /data

USER appuser
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "price_analyst.main:app", "--app-dir", "/app/backend/src", "--host", "0.0.0.0", "--port", "8000"]
