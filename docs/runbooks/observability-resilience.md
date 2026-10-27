# Observability and resilience baseline

This is a framework baseline, not evidence that a production SLO has been met. Production targets must be reviewed after representative traffic, capacity, and failure data exist.

## Signal contract

Every ACCOS JSON log has `timestamp`, `level`, `service`, `environment`, `event`, request/trace/task IDs, optional workflow/agent/model-call IDs, pseudonymous workspace/project references, `duration_ms`, `outcome`, and stable `error_code`. Raw workspace/project/user IDs, credentials, Prompt, Memory, and content fields are redacted. Request logs use route templates rather than identifier-bearing URLs.

`GET /metrics` exposes only registered low-cardinality metric families. `GET /api/v1/system/observability` requires `workspace:read` and reports whether metrics and OTLP are configured, a metric-name inventory, Worker heartbeat freshness, and authoritative Outbox backlog. OTLP export is optional and fail-open; exporter failure never changes liveness or readiness.

Start the local signal stack with:

```powershell
docker compose --env-file .env -f infra/compose.yaml --profile observability up -d
```

Set `ACCOS_OTLP_ENDPOINT=http://127.0.0.1:4318` for host-run API/Worker processes. Traces are visible at `http://127.0.0.1:16686`; OTLP metrics are visible at `http://127.0.0.1:9090`. Leaving the endpoint empty must remain a supported normal mode.

## Initial SLI/SLO and alert baseline

| Surface             | SLI                                         |                    Initial objective | Alert condition                                 |
| ------------------- | ------------------------------------------- | -----------------------------------: | ----------------------------------------------- |
| API availability    | non-5xx requests / requests                 |                   99.5% over 30 days | 5xx ratio > 2% for 10 minutes                   |
| API latency         | route-template request duration             |                     95% under 750 ms | p95 > 1.5 s for 15 minutes                      |
| Workflow completion | terminal successful / terminal runs         |          99% for framework workflows | failed/dead-letter increase for 10 minutes      |
| Worker freshness    | last heartbeat age                          |                     under 20 seconds | stale or unavailable for 2 minutes              |
| Outbox delivery     | oldest unpublished event age                |                     under 60 seconds | age > 5 minutes or backlog rises for 15 minutes |
| Model gateway       | successful attempts / attempted calls       | 98% in configured real-provider mode | circuit open or fallback failures for 5 minutes |
| Object storage      | successful operations / operations          |                                99.9% | errors > 1% for 10 minutes                      |
| Recovery            | verified logical backup age                 |                      RPO <= 24 hours | no verified backup for 26 hours                 |
| Recovery time       | isolated restore and integrity verification |                       RTO <= 4 hours | latest drill fails or exceeds target            |

No alert should contain IDs or content. Diagnose with the request/trace ID in logs, then follow Workflow ID -> Task ID -> Agent/Model call ledger -> Outbox sequence -> storage outcome. A single browser action receives request and trace IDs in response headers; downstream durable records retain the correlation ID.

## Dependency-failure procedure

1. Check `/ready`, `/api/v1/system/health`, and `/api/v1/system/observability`; distinguish critical dependency failure from optional AI/OTLP degradation.
2. Use the trace ID to inspect structured logs. Never paste credentials or raw content into incident notes.
3. Confirm finite timeout/retry/circuit state. Do not raise retries before checking downstream capacity.
4. PostgreSQL unavailable: stop writes, preserve Outbox and task state, restore service, then verify migrations and backlog drain.
5. Redis/queue unavailable: keep PostgreSQL authoritative; Outbox publication retries remain durable. Rebuild disposable Memory projections after Redis recovers.
6. Object storage unavailable: metadata remains authoritative; failed uploads retain compensation checkpoints. Reconcile object presence before changing processing status.
7. OTLP unavailable: application work continues; use local JSON logs and `/metrics`, then restore the collector independently.

## Queue buildup and disk pressure

For queue buildup, inspect Outbox backlog/age, Worker heartbeat, task leases, Redis availability, and consumer errors in that order. Scale consumers only after confirming idempotency and downstream capacity. Do not delete Outbox or task rows to reduce a graph.

For disk pressure, stop new uploads and nonessential writes, identify PostgreSQL/WAL, MinIO versions, Redis AOF, logs, and Prometheus retention separately, and expand or rotate the correct bounded store. Never delete a database volume, MinIO version, or backup during an incident. Prometheus local data and Redis projections are disposable only after the authoritative services are safe.

## Migration failure and rollback

Never retry a partially applied migration blindly. Capture the Alembic revision, database log, and backup manifest; use `alembic current` and `alembic check`. Prefer restoring an isolated backup to validate the correction. Application rollback must use a schema-compatible version. Stage 22 adds no domain schema and keeps `0012_extension_graph_projection` as head.
