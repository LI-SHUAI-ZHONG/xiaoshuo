#!/usr/bin/env sh
set -eu

if [ "${1:-}" != "--confirm-data-loss" ]; then
  echo "DESTRUCTIVE: this removes all ACCOS PostgreSQL, Redis, and MinIO local volumes." >&2
  echo "Re-run with --confirm-data-loss." >&2
  exit 2
fi

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
environment_file="$repository_root/.env"
compose_file="$repository_root/infra/compose.yaml"
if [ ! -f "$environment_file" ]; then
  echo "Missing .env; refusing to guess which Compose project owns the volumes." >&2
  exit 2
fi

docker_command=docker
if ! command -v "$docker_command" >/dev/null 2>&1; then
  if command -v cygpath >/dev/null 2>&1 && [ -n "${LOCALAPPDATA:-}" ]; then
    docker_candidate="$(cygpath -u "$LOCALAPPDATA")/Programs/DockerDesktop/resources/bin/docker.exe"
    if [ -x "$docker_candidate" ]; then
      docker_command=$docker_candidate
    fi
  fi
  if ! command -v "$docker_command" >/dev/null 2>&1 && [ ! -x "$docker_command" ]; then
    echo "Docker CLI is unavailable." >&2
    exit 3
  fi
fi

echo "WARNING: removing ACCOS local infrastructure containers and named data volumes." >&2
exec "$docker_command" compose --env-file "$environment_file" --file "$compose_file" down --volumes --remove-orphans
