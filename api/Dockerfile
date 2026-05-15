FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY src ./src
RUN uv sync --no-dev

# Migration tooling — alembic.ini lives at /app, migrations under /app/alembic.
# Required so `alembic upgrade head` works inside the container during deploy.
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000
CMD ["uv", "run", "fastapi", "run", "src/paczkomat_atlas_api/main.py", "--host", "0.0.0.0", "--port", "8000"]
