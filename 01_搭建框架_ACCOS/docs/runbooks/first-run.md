# First run: `v0.1-skeleton`

This runbook starts ACCOS from a clean checkout with only Fake/Null providers. It does not need an
AI key, does not create creative content, and does not push or deploy an image.

## Prerequisites

- Docker Engine or Docker Desktop with Compose v2.
- Python 3.12.14, uv 0.12.7, Node.js 22.23.2, and Corepack/pnpm 11.25.0 for host-side checks.
- Free loopback ports 3000, 5432, 6379, 8000, 9000, and 9001.

From the repository root, confirm that both `改进资料.txt` and `执行.txt` are present. Do not create a
second nested checkout.

## Configure

Copy `.env.example` to `.env`. Replace every `replace-with-*` value with a local-only value. For the
local identity used by the smoke test, also set:

```dotenv
ACCOS_DEV_IDENTITY_ENABLED=true
ACCOS_DEV_IDENTITY_TOKEN=<local-random-token>
ACCOS_DEV_IDENTITY_ACTOR_ID=<uuid-v4>
ACCOS_DEV_IDENTITY_WORKSPACE_ID=<uuid-v4>
ACCOS_DEV_IDENTITY_APPROVER_TOKEN=<different-local-random-token>
ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID=<different-uuid-v4>
```

Keep every real-provider and extension flag `false`. Never put a production credential in `.env`.

## Install and verify locks

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
corepack pnpm run security:local
```

POSIX shell:

```sh
sh scripts/install.sh
corepack pnpm run security:local
```

## Start the complete container stack

This command builds the API, Worker, and Studio images, starts PostgreSQL/pgvector, Redis, and
MinIO, enables bucket versioning, migrates the empty database, and waits for readiness:

```powershell
docker compose --env-file .env -f infra/compose.yaml --profile application up --detach --build --wait --wait-timeout 240
```

Verify the public boundaries:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/live
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-WebRequest http://127.0.0.1:3000/status -UseBasicParsing
docker compose --env-file .env -f infra/compose.yaml ps
```

Studio is at `http://127.0.0.1:3000`. The API is at `http://127.0.0.1:8000`. Containers run as a
non-root user, expose only loopback ports, and receive credentials at runtime.

## Run the vertical smoke

Use the same local identity values from `.env`:

```powershell
uv run --frozen python scripts/full_stack_smoke.py `
  --workspace-id $env:ACCOS_DEV_IDENTITY_WORKSPACE_ID `
  --token $env:ACCOS_DEV_IDENTITY_TOKEN `
  --approver-token $env:ACCOS_DEV_IDENTITY_APPROVER_TOKEN `
  --evidence .tmp-stage23/full-stack-smoke.json
```

The smoke creates only the fixed technical fixture. It proves project/revision/asset persistence,
Fake embedding with citation, budgeted memory context, Director/Workflow/Fake Agent/Fake
Model/Fake Tool execution, structural gates, human approval, metrics, audit-producing writes, SSE
terminal state, idempotency, and workspace isolation.
The requester is first denied self-approval, then the distinct local approver completes the human
decision; both identities are disabled in production.

Run all host-side checks separately:

```powershell
corepack pnpm run check
```

## Stop while preserving data

```powershell
docker compose --env-file .env -f infra/compose.yaml --profile application down --remove-orphans
```

Named PostgreSQL, Redis, MinIO, and Prometheus volumes remain. A later `up` reuses them. Only use
`down --volumes` for an explicitly disposable environment; it irreversibly removes those named
volumes.

## Failure triage

- If migration fails, stop application containers, preserve volumes, and follow
  `docs/runbooks/database-migrations.md`.
- If readiness is red, inspect `docker compose ... ps` and sanitized container logs; do not paste
  `.env` values into an issue.
- If a workflow is pending, restart the Worker. PostgreSQL retains the authoritative run, task, and
  Outbox state; Redis is not a recovery source.
- For backup/restore and narrow-target safety rules, use
  `docs/runbooks/backup-disaster-recovery.md`.
