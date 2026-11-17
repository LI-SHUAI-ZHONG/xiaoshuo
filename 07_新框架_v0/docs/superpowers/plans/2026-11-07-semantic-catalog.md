# Semantic source ledger implementation plan

> **For agentic workers:** Execute this bounded delegated plan in the current session. No commits, source-data writes, formal audit, or full pytest run; the root agent owns integration and final regression.

**Goal:** Audit every current SourceDesk owner against its original source and cache discovery metadata without granting semantic or execution approval.

**Architecture:** `source_context.py` reads exact owner metadata and complete saved review context, and provides an audit-only hash-verified fragment cache restored in `finally`. `semantic_catalog.py` compiles each original, independently checks clause locations/values and all original field dispositions, then optionally writes a new versioned SQLite discovery index. Normal runtime source reads remain unchanged.

**Tech Stack:** Python standard library, existing SourceDesk/compiler, SQLite, pytest.

**Spec:** Delegated 2026-11-07 task: source_context, audit_semantic_sources, load_semantic_metadata; root agent integrates SourceDesk/CLI.

## Constraints and approach

- Only new modules/tests/docs inside 07; no source-directory, catalog/adjudication DB, formal project, model, or commit changes.
- Three public signatures remain as requested. Context includes exact owner ref plus full top-level review refs/layer_contract.
- New index files are immutable versions; no overwriting, deletion, or moving existing artifacts. Missing/stale/incomplete cache returns `{}`.
- Fingerprints include compiler/code, source set, current owner ledger and input DB stat/metadata. Cache is discovery/trace data only.
- Audit JSON details stream rows to an explicitly requested new file; every compiled contract retains originals and independent field dispositions.
- Each new source module stays below 400 lines. Tests and temporary catalogs use a unique directory below 07/.venv.

## Review focus

- Exact current owner identity and full review context, including owners absent from primary positions.
- Whole fragment and unit-slice corruption, with cache restoration on failure.
- Clauses with valid-looking hashes but wrong JSON values, missing fields, or obsolete spans.
- Cache invalidation after compiler, source-set, or adjudication changes; incomplete index cannot become current.
- Source clauses, semantic/native review needs, source issues, dispositions and explicit stages remain separate from semantic success.

## Tasks

- [ ] Add small real-catalog tests for context, full-field fidelity, corruption, restoration and cache invalidation; run the focused file and observe missing-feature failures.
- [ ] Implement exact context and audit-only verified read cache; run focused context/corruption tests.
- [ ] Implement streaming per-owner audit, versioned discovery index and fingerprint-gated metadata loader; run the focused file.
- [ ] Check the two module line counts, whitespace and only the assigned file diffs. Report actual focused results; root performs full audit and suite.
