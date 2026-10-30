# Stage 28 Versioned DAG Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing durable Workflow/Agent runtime into the single versioned DAG, frozen-input, recoverable scheduling and orchestration system required by R024–R030.

**Architecture:** Evolve the existing `modules/workflows` aggregate and SQL repository in place. A published definition version freezes node/edge contracts; a run materializes eligible nodes only after required predecessors and frozen inputs are satisfied, while PostgreSQL remains the state, lease, schedule and event authority. The existing Worker, Outbox, approval policy, Agent supervisor and models.v2 runtime remain the only execution paths.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, SQLAlchemy 2/PostgreSQL, Celery/Redis Outbox relay, Next.js/React/TypeScript, OpenAPI-generated client.

**Spec:** `后续执行/步骤/28_依赖工作流调度与总控.md`

## Global Constraints

- R024–R030 and T024–T030 are the complete Stage 28 scope.
- Do not create a second scheduler, approval engine, Agent runtime, content store, Outbox, or body-of-work fact model.
- Published Workflow/role versions and frozen run inputs are immutable; old and in-flight runs never switch to a newer version.
- Conditions use a bounded declarative predicate set only; never execute user/model Python or JavaScript.
- Iteration is represented by bounded child/linked runs, not cyclic graph edges.
- Events, logs and handoffs contain references, hashes and summaries only, never body content, secrets or private chain-of-thought.
- Build Stage 28 tests and fixtures now, but do not execute project tests, services, migrations, database queries or real model calls before Stage 45 (project decision D19).
- Static-only validation and offline contract/client generation are allowed.
- Source migration head is `0015_model_execution`; append `0016_workflow_dag` and do not edit old migrations.

## Review Focus

- A diamond graph must dispatch both ready branches once and schedule the join only after every non-skipped dependency succeeds.
- A missing, unauthorized or stale mandatory reference must block execution and must never produce a fabricated ReadReceipt.
- A lease-losing worker must be fenced from settlement; an unknown external result must not be blindly retried.
- Schedule due claims must be unique across workers and implement explicit catch-up/skip/fire-once misfire behavior across time zones.
- Role/Workflow edits must affect only newly created runs; disabled roles and revoked grants must prevent new dispatch without mutating in-flight snapshots.

---

### Task 1: DAG, frozen input, receipt and scheduling contracts

**Files:**
- Modify: `services/core/src/accos/modules/workflows/domain.py`
- Modify: `services/core/src/accos/modules/workflows/ports.py`
- Modify: `services/core/src/accos/modules/workflows/public.py`
- Create: `services/core/src/accos/modules/workflows/validation.py`
- Create: `services/core/resources/workflows/creative_orchestration.v1.json`
- Test: `services/core/tests/test_workflows_stage28.py`

**Interfaces:**
- Consumes: existing `WorkflowDefinition`, `StepDefinition`, `WorkflowRun`, `StepRun`, `TaskRun`, `RetryPolicy`.
- Produces: `ConditionExpression`, `StageRequirement`, `ResolvedInput`, `StepInputManifest`, `ReadReceipt`, `DependencyEdge`, `WorkflowSchedule`, `RoleDescriptorVersion`; `validate_definition(definition) -> None`; repository and resolver ports used by later tasks.

- [ ] **Step 1: Author T024/T025/T028/T030 contract tests without executing them**

  Cover cycle rejection, linear legacy edge adaptation, diamond readiness, bounded condition/iteration validation, immutable input digests, receipt invariants, schedule/misfire validation and role/grant version validation.

- [ ] **Step 2: Implement immutable domain contracts and graph validation**

  Keep positional fields for legacy reads, derive missing linear dependencies for v1 definitions, topologically validate explicit DAGs, and constrain predicates to equality/presence/status checks over named predecessor outputs.

- [ ] **Step 3: Add the packaged default DAG resource**

  Define a content-free, bounded orchestration workflow with explicit schemas, executors, requirements, approval/budget/retry/timeout metadata and no user seed data.

- [ ] **Step 4: Run static syntax/type/format checks for only the changed source and resource files**

  Expected: exit 0; no project tests are run.

- [ ] **Step 5: Record task completion and D19 test deferral in the Stage 28 ledger**

### Task 2: SQL persistence, migration and DAG scheduling transitions

**Files:**
- Create: `services/core/migrations/versions/0016_workflow_dag.py`
- Modify: `services/core/src/accos/adapters/workflows/persistence.py`
- Create: `services/core/src/accos/adapters/workflows/dependencies.py`
- Modify: `services/core/src/accos/adapters/workflows/__init__.py`
- Test: `services/core/tests/test_workflows_stage28_sql.py`

**Interfaces:**
- Consumes: Task 1 domain contracts and `WorkflowRepository`/`DependencyResolver` protocols.
- Produces: durable definition edges, manifests, receipts, dependency edges, compensation attempts, schedules/due claims, linked-run lineage, role versions and grants; atomic ready-node dispatch and fencing-token settlement.

- [ ] **Step 1: Author T024/T025/T027/T028 SQL tests without executing them**

  Cover immutable definition versions, concurrent join scheduling, stale-input propagation, expired lease settlement rejection, operation-key uniqueness, compensation/unknown/dead-letter records, unique due claims and linked retry runs.

- [ ] **Step 2: Append migration `0016_workflow_dag`**

  Expand existing tables and add owner-scoped tables/indexes/constraints; backfill explicit linear edges for existing definitions without changing existing run snapshots.

- [ ] **Step 3: Replace `_advance(position + 1)` with atomic readiness evaluation**

  Schedule every eligible node once, treat skipped dependencies as satisfied with a recorded reason, complete the run only when all materialized terminal nodes settle, and preserve existing approval/pause/cancel behavior.

- [ ] **Step 4: Add durable input freezing, receipts, dependency invalidation, schedule claims and compensation records**

  Every write shares the owning workflow transaction and Outbox boundary; settlement compares the claimed fencing token.

- [ ] **Step 5: Run migration import, ORM metadata, syntax, type and format static checks only**

  Expected: `0016` imports, models register once, and checks exit 0; no migration is applied and no database is queried.

- [ ] **Step 6: Record task completion and D19 test deferral in the Stage 28 ledger**

### Task 3: Application services, Worker recovery, Director plans and bounded meetings

**Files:**
- Modify: `services/core/src/accos/modules/workflows/application.py`
- Create: `services/core/src/accos/modules/workflows/scheduling.py`
- Modify: `services/core/src/accos/modules/agents/domain.py`
- Modify: `services/core/src/accos/modules/agents/ports.py`
- Modify: `services/core/src/accos/modules/agents/application.py`
- Modify: `services/core/src/accos/modules/agents/definitions.py`
- Create: `services/core/src/accos/modules/agents/meetings.py`
- Modify: `services/core/src/accos/modules/agents/public.py`
- Modify: `services/core/src/accos/composition/root.py`
- Test: `services/core/tests/test_agents_stage28.py`

**Interfaces:**
- Consumes: Task 2 repository operations, models.v2 prompt/profile pins, existing `ApprovalPolicyPort`, Outbox and `AgentSupervisor`.
- Produces: definition draft/publish/run/retry APIs, `WorkflowScheduler.tick(now)`, constrained `MasterOrchestrator.submit_plan`, bounded `RoleMeetingService`, versioned role registry and frozen task routing snapshots.

- [ ] **Step 1: Author T026/T027/T028/T030 application tests without executing them**

  Cover invalid/cyclic Director plans, server-side permission/budget narrowing, meeting round/parallel/call limits, decision summaries without reasoning traces, cancellation/unknown settlement and role disable/grant revocation.

- [ ] **Step 2: Implement publish and run preflight services**

  Resolve and freeze basic content references, leave one explicit `ContextBuilder` port for Stage 30, and map unresolved mandatory inputs to waiting states rather than synthetic success.

- [ ] **Step 3: Extend Worker recovery and scheduler maintenance**

  Process due schedules, approval expiry, recoverable leases and dead-letter redrive through the same workflow repository/Worker path; external calls receive stable operation keys.

- [ ] **Step 4: Generalize MasterOrchestrator and add bounded role meetings**

  Validate typed plan nodes against published executors/roles/grants, materialize a definition version, and persist proposal/decision summaries only.

- [ ] **Step 5: Compose one API/Worker runtime implementation**

  API and worker use the same persistent registries, definition catalog, dependency resolver and scheduler; test/demo fakes remain isolated.

- [ ] **Step 6: Run changed-source syntax/type/format and import-boundary static checks only**

- [ ] **Step 7: Record task completion and D19 test deferral in the Stage 28 ledger**

### Task 4: Resource APIs, SSE history and generated client

**Files:**
- Create: `services/core/src/accos/entrypoints/api/v1/workflow_schemas.py`
- Create: `services/core/src/accos/entrypoints/api/v1/workflow_router.py`
- Modify: `services/core/src/accos/entrypoints/api/v1/router.py`
- Modify: `services/core/src/accos/entrypoints/api/v1/stage17_router.py`
- Modify: `services/core/src/accos/entrypoints/api/v1/stage17_schemas.py`
- Modify: `services/core/tests/test_api_v1.py`
- Modify: `packages/api-client/openapi.json`
- Modify: `packages/api-client/src/generated/schema.ts`

**Interfaces:**
- Consumes: Task 3 services and authorized security context dependencies.
- Produces: project Workflow definition draft/validate/publish/list, run collection/detail/inputs/receipts/dependencies/retry, workspace schedules, role descriptors/grants and resumable event endpoints with generated TypeScript types.

- [ ] **Step 1: Author T029/T030 API contract cases without executing them**

  Include If-Match/idempotency, workspace/project scope denial, terminal retry returning a new linked run id, cursor recovery, and secret/body-free response assertions.

- [ ] **Step 2: Implement resource routers and response mappers**

  Preserve old Stage 17 endpoints as compatibility delegates; new list/create/update operations use explicit resources and stable pagination/order.

- [ ] **Step 3: Export OpenAPI and regenerate the TypeScript client offline**

  Expected: generated artifacts match the application schema; this is contract generation, not a service/test run.

- [ ] **Step 4: Run targeted schema syntax/type/format static checks only**

- [ ] **Step 5: Record task completion and D19 test deferral in the Stage 28 ledger**

### Task 5: Studio Workflow/role management and run observability

**Files:**
- Modify: `apps/studio/src/lib/api/query-keys.ts`
- Modify: `apps/studio/src/lib/api/queries.ts`
- Modify: `apps/studio/src/lib/api/mutations.ts`
- Modify: `apps/studio/src/features/workflows/workflow-monitor.tsx`
- Modify: `apps/studio/src/features/workflows/workflow-run-detail.tsx`
- Create: `apps/studio/src/features/workflows/workflow-definition-editor.tsx`
- Create: `apps/studio/src/features/agents/role-descriptor-manager.tsx`
- Modify: `apps/studio/src/features/agents/agent-center.tsx`
- Modify: `tests/unit/studio-stage20.test.ts`
- Create: `tests/unit/studio-stage28.test.ts`
- Create: `tests/e2e/studio-stage28.spec.ts`

**Interfaces:**
- Consumes: Task 4 generated API client only.
- Produces: definition version editor/publisher, DAG node/dependency view, run history, frozen inputs/receipts/budget/approval visibility, pause/resume/cancel/linked retry, schedule controls and role/tool-grant management.

- [ ] **Step 1: Author T029/T030 unit/E2E cases without executing them**

  Cover empty/configuration/permission states, no manual-id requirement for normal navigation, immutable in-flight version display and linked retry navigation.

- [ ] **Step 2: Implement generated-client queries and mutations**

- [ ] **Step 3: Implement definition, monitoring, schedule and role UI**

  Use accessible tables/forms as the baseline; the full visual canvas remains Stage 34, but every Stage 28 operation must be usable now.

- [ ] **Step 4: Run TypeScript and Prettier static checks for changed files only**

- [ ] **Step 5: Record task completion and D19 test deferral in the Stage 28 ledger**

### Task 6: Registers, handoff and static construction evidence

**Files:**
- Modify: `docs/contracts/migrations.json`
- Modify: `docs/contracts/ownership.json`
- Modify: `docs/contracts/implementation-register.json`
- Modify: `docs/contracts/test-registration.json`
- Modify: `后续执行/需求覆盖矩阵.csv`
- Modify: `后续执行/进度.json`
- Create: `docs/handoffs/28.md`
- Create: `后续执行/证据/第28步施工_20261027.json`

**Interfaces:**
- Consumes: all preceding implementation and static-check outputs.
- Produces: continuous R024–R030/T024–T030 records, migration ownership/hash evidence, recovery baseline reference and the Stage 29 handoff.

- [ ] **Step 1: Register implementation, tests, migration and owned tables**

- [ ] **Step 2: Perform the permitted full static construction checks**

  Include Python syntax/mypy, changed-file Ruff formatting, TypeScript types, Prettier, JSON/resource hashes, ORM registration and OpenAPI/client consistency without invoking project tests/services/migrations/database/model calls.

- [ ] **Step 3: Write evidence and handoff with exact NOT_RUN boundaries**

- [ ] **Step 4: Set Stage 28 to `IMPLEMENTED_UNTESTED` only if every construction deliverable is present; otherwise keep `IN_PROGRESS` with concrete next action**

- [ ] **Step 5: Self-review plan coverage, interface consistency and Review Focus mutations**

