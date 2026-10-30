# `v0.1-skeleton` traceability matrix

Statuses mean exactly: `implemented skeleton` is executable and automatically tested; `port only`
is a disabled boundary with no claimed business implementation; `intentionally deferred` is outside
the skeleton scope.

| Source objective                                                 | Current module or contract                                             | Repeatable evidence                                                    | Status                 |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------- |
| Creator workspace and empty project lifecycle                    | Identity, RBAC, Projects, Studio project shell                         | `test_identity.py`, `test_projects_assets.py`, live Stage 23 smoke     | implemented skeleton   |
| Versioned technical artifacts and object assets                  | Project revision repository, Asset port, S3 adapter                    | `test_projects_assets.py`, `test_persistence.py`, recovery drill       | implemented skeleton   |
| Knowledge ingestion and traceable retrieval                      | Knowledge workflow, Fake embedder, pgvector, Citation contract         | `test_knowledge.py`, live Stage 23 smoke                               | implemented skeleton   |
| Seven-scope memory and budgeted context                          | Memory service, conflict proposal, Context Package                     | `test_memory.py`, live Stage 23 smoke                                  | implemented skeleton   |
| Director and controlled Agent orchestration                      | Agent registry/supervisor, `framework_smoke`, Fake model/tool gateways | `test_agents.py`, `test_model_tool_gateways.py`, live Stage 23 smoke   | implemented skeleton   |
| Durable asynchronous execution                                   | PostgreSQL Workflow/Task/Outbox, Redis/Celery adapter, Worker          | `test_workflows.py`, `test_persistence.py`                             | implemented skeleton   |
| Canon and quality gates                                          | Deterministic Consistency and schema-only Quality services             | `test_consistency_quality.py`, live Stage 23 smoke                     | implemented skeleton   |
| Feedback, metrics, and controlled improvement                    | Feedback registry, diagnostics, audited proposal state machine         | `test_feedback_evolution.py`, live Stage 23 smoke                      | implemented skeleton   |
| Human control over protected changes                             | RBAC authorizer, approval records, immutable safety controller         | negative identity/agent/evolution tests, live Stage 23 smoke           | implemented skeleton   |
| REST, OpenAPI, generated TS client, SSE                          | `/api/v1`, OpenAPI snapshot, `@accos/api-client`, resumable events     | `test_api_v1.py`, `api:check`, Playwright                              | implemented skeleton   |
| Studio creator and system workspaces                             | Next.js routes, Query providers, status/error boundaries               | Vitest and Playwright suites                                           | implemented skeleton   |
| Observability and disaster recovery                              | Structured logs, metrics/traces, backup/verify/restore/drill           | unit coverage, Stage 23 Moto drill; CI MinIO repeat pending            | implemented skeleton   |
| OCI delivery baseline                                            | API/Worker/Studio Docker targets and application Compose profile       | image metadata gate, Trivy, Syft, live container E2E                   | implemented skeleton   |
| Multimodal inputs                                                | Typed capability manifests and Null adapters                           | `test_extensions.py`                                                   | port only              |
| Graph projection                                                 | Disabled feature flag and scoped graph port                            | `test_extensions.py`, migration 0012                                   | port only              |
| Collaboration, rights, marketplace, reputation, growth           | Disabled manifests and fail-closed Null boundaries                     | `test_extensions.py`                                                   | port only              |
| External knowledge network and research team                     | Deferred acquisition/verification ports                                | `test_extensions.py`                                                   | port only              |
| Real model/tool providers and production prompts                 | Provider/tool interfaces only; real calls default off                  | gateway and configuration negative tests                               | intentionally deferred |
| Creative content logic, examples, and corpora                    | No fixture or production content in the skeleton                       | content-boundary review and secret/content-free fixtures               | intentionally deferred |
| Payment, trading, autonomous code changes, autonomous deployment | No executable capability                                               | architecture and safety policy tests                                   | intentionally deferred |

The detailed requirement-to-test map remains distributed across `docs/handoffs/01.md` through
`docs/handoffs/23.md`; this matrix is the release-level index, not a replacement for those proofs.
