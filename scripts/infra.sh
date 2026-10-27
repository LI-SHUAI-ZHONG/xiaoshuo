#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compose_file="$repository_root/infra/compose.yaml"
environment_file="$repository_root/.env"
command_name=${1:-status}

case "$command_name" in
  up | down | status | check) ;;
  *)
    echo "Usage: $0 <up|down|status|check>" >&2
    exit 2
    ;;
esac

if [ ! -f "$environment_file" ]; then
  echo "Missing .env. Copy .env.example to .env and replace every local credential placeholder." >&2
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
    echo "Docker CLI is unavailable. Install and start Docker Desktop or Docker Engine with Compose." >&2
    exit 3
  fi
fi

compose() {
  "$docker_command" compose --env-file "$environment_file" --file "$compose_file" "$@"
}

check_infrastructure() {
  compose --profile tools run --rm --no-deps postgres-check
  compose --profile tools run --rm --no-deps redis-check
  compose --profile tools run --rm --no-deps minio-check
  echo "Infrastructure self-check passed: PostgreSQL/pgvector, Redis, and S3 read/write are healthy."
}

cd "$repository_root"
compose config --quiet

case "$command_name" in
  up)
    compose up --detach --wait --wait-timeout 180 postgres redis minio
    compose --profile tools run --rm --no-deps minio-init
    check_infrastructure
    ;;
  down)
    compose down --remove-orphans
    echo "Infrastructure stopped. Named volumes were preserved."
    ;;
  status)
    compose ps
    ;;
  check)
    check_infrastructure
    ;;
esac
