# Backup, restore, export, and disaster recovery

PostgreSQL and versioned object storage are authoritative. Redis contains queues, locks, cache, heartbeat, and disposable projections; it is rebuilt, not restored as a source of business truth.

## Safety rules

- Run destructive drills only in generated `accos_drill_*` databases and `accos-drill/*` object prefixes.
- Restore refuses existing databases and nonempty object prefixes. It never overwrites a record or object.
- Backup targets must be explicit narrow directories; filesystem roots, the home directory, and the repository root are rejected.
- Backups are never deleted automatically. Store production copies encrypted, access-controlled, off-host, and with retention managed outside this script.
- A manifest records application/schema versions, database table counts, object versions, byte counts, and SHA-256 checksums. Verification precedes every restore.

## Commands

```powershell
uv run --frozen python scripts/recovery.py backup --target D:\accos-backups\accos-2026-09-18
uv run --frozen python scripts/recovery.py verify --source D:\accos-backups\accos-2026-09-18
uv run --frozen python scripts/recovery.py restore --source D:\accos-backups\accos-2026-09-18 --database-target accos_restore_ticket123 --object-prefix accos-restore/ticket123
uv run --frozen python scripts/recovery.py drill --target D:\accos-backups\accos-drill-2026-09-18
```

The isolated drill performs backup, restores into generated targets, destroys only cloned technical schema metadata, restores again, verifies table counts and object checksums, records actual timings, and removes the generated database/object prefix. Its backup and `drill-result.json` remain for evidence.

## Workspace/project portability

```powershell
uv run --frozen python scripts/project_transfer.py export --target D:\accos-exports\project-1 --workspace-id <uuid> --project-id <uuid>
uv run --frozen python scripts/project_transfer.py validate-import --source D:\accos-exports\project-1
```

The export manifest includes scoped authoritative rows, asset references/versions, audit rows that can be safely scoped, schema/application versions, per-table counts, and checksums. Credential-like columns are redacted. Validation checks checksum, schema compatibility, and primary-key conflicts; it performs no writes. Any conflict blocks import and can never overwrite existing data.

## Recovery decision flow

1. Declare the recovery point and preserve the failed environment for evidence.
2. Verify the selected manifest and checksum before provisioning a target.
3. Restore PostgreSQL to a new database and objects to a new prefix.
4. Compare schema revision, all table counts, object sizes/hashes, projects, Revisions, workflow/task state, audit rows, and object manifest.
5. Point a test runtime at the restored targets and run readiness plus a read-only smoke test.
6. Obtain human approval before any traffic switch. Retain the old target for rollback.
7. Recreate Redis, then rebuild disposable Memory/search projections from PostgreSQL and objects.

## Missing object and failed restore

If metadata references a missing/corrupt object, do not delete metadata or fabricate content. Mark the version diagnostically, locate the checksum in a verified backup/version history, restore to an isolated prefix, compare SHA-256, then promote through an approved change. If restore fails, keep the new target isolated, capture logs and manifest IDs, correct capacity/configuration, and retry with another new target.

Initial framework objectives are RPO 24 hours and RTO 4 hours. They are planning targets only until scheduled backups and repeated representative drills provide production evidence.
