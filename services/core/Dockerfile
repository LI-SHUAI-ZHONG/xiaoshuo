# syntax=docker/dockerfile:1.7

FROM python:3.12.14-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN python -m pip install --no-cache-dir uv==0.12.7

COPY pyproject.toml uv.lock ./
COPY services/core/pyproject.toml services/core/pyproject.toml
COPY services/core/src services/core/src
COPY services/core/resources services/core/resources
COPY services/core/migrations services/core/migrations
COPY services/core/alembic.ini services/core/alembic.ini

RUN uv sync --frozen --no-dev --all-packages

FROM python:3.12.14-slim-bookworm AS runtime

ARG ACCOS_VERSION=0.1.0-skeleton
ARG ACCOS_REVISION=unknown

LABEL org.opencontainers.image.title="ACCOS Core" \
      org.opencontainers.image.description="ACCOS API and Worker skeleton runtime" \
      org.opencontainers.image.version="${ACCOS_VERSION}" \
      org.opencontainers.image.revision="${ACCOS_REVISION}" \
      org.opencontainers.image.source="https://invalid.local/accos" \
      org.opencontainers.image.licenses="Proprietary"

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ACCOS_ENV=container

RUN groupadd --system --gid 10001 accos \
    && useradd --system --uid 10001 --gid accos --home-dir /nonexistent --shell /usr/sbin/nologin accos

WORKDIR /app

COPY --from=builder --chown=accos:accos /app/.venv /app/.venv
COPY --from=builder --chown=accos:accos /app/services/core /app/services/core
COPY --chown=accos:accos uv.lock /app/dependency-manifests/uv.lock

USER 10001:10001

FROM runtime AS api

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=6 \
  CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/live', timeout=2).read()"]

CMD ["python", "-m", "accos.entrypoints.api"]

FROM runtime AS worker

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=6 \
  CMD ["python", "-c", "import os; os.kill(1, 0)"]

CMD ["python", "-m", "accos.entrypoints.worker"]

