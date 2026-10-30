# `v0.1-skeleton` final acceptance

## Decision

**PARTIAL**

The release candidate is implemented and every host-executable gate passes, but this checkout cannot
be labeled `v0.1-skeleton` until the Docker delivery job runs successfully. This machine has no OCI
builder, so the three image builds, clean Compose first run, MinIO recovery repeat, image
vulnerability scan, and SBOM generation have not been executed here.

## Binary checklist

- [ ] Clean checkout installs and starts once by following `docs/runbooks/first-run.md` — encoded in
      CI, not executed on this Docker-less host.
- [x] Empty migration and native API/Worker/Studio readiness all pass; container readiness remains
      part of the separate image/clean-Compose blockers below.
- [x] OpenAPI snapshot and generated TypeScript client have no drift.
- [x] Complete live Fake E2E and all failure paths pass against isolated PostgreSQL, Redis, and Moto;
      the same profile is encoded for Compose CI.
- [x] Worker restart recovery and duplicate-request no-duplicate-side-effect tests pass.
- [x] Workspace/Project isolation, RBAC, Tool permissions, budgets, and human approval negative tests
      pass.
- [x] Logs, Trace, metrics, and audit correlation tests pass without sensitive content.
- [ ] PostgreSQL backup plus MinIO object manifest restoration passes — the Stage 23 Moto repeat
      restored 68 tables and 3 versioned objects with matching checksums; real MinIO remains CI
      evidence.
- [ ] API, Worker, and Studio images build as non-root without real secrets — Dockerfiles and static
      gates pass; runtime image inspection is awaiting CI.
- [x] Every future capability is explicitly `port only`, disabled, or intentionally deferred.

An unchecked item is release-blocking by definition. A Git tag, image push, artifact upload, or
deployment is not authorized by this document.

## Evidence routes

- Local static and test commands are recorded in `docs/handoffs/23.md`: 375 Python tests at 100%
  statement/branch coverage, 28 Vitest tests, 7 Playwright tests, a live Fake smoke, production build,
  and an isolated Moto recovery drill all pass.
- CI stages are `supply-chain -> quality -> integration -> delivery` in
  `.github/workflows/quality.yml`.
- Requirement coverage is indexed in `docs/traceability-v0.1-skeleton.md`.
- The delivery job generates runner-local `full-stack-smoke.json`, restore evidence, SPDX SBOMs,
  lockfiles, and `release-manifest.json`, prints their SHA-256 values, then removes disposable
  services. It deliberately does not upload those files or push images.
