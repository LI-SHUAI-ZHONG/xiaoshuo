"""Additive storage for source-grounded, multi-level corpus analysis."""

SCHEMA = '''
CREATE TABLE IF NOT EXISTS corpus_structures (
 book_id TEXT PRIMARY KEY REFERENCES staging_books(id), latest_version INTEGER NOT NULL,
 approved_version INTEGER, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS corpus_structure_versions (
 book_id TEXT NOT NULL REFERENCES corpus_structures(book_id), version INTEGER NOT NULL,
 source_sha256 TEXT NOT NULL, body_json TEXT NOT NULL, body_sha256 TEXT NOT NULL,
 coverage_json TEXT NOT NULL, job_id TEXT, created_at TEXT NOT NULL,
 PRIMARY KEY(book_id,version));
CREATE TABLE IF NOT EXISTS corpus_structure_reviews (
 book_id TEXT NOT NULL, version INTEGER NOT NULL, decision TEXT NOT NULL,
 note TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(book_id,version),
 FOREIGN KEY(book_id,version) REFERENCES corpus_structure_versions(book_id,version));
CREATE TABLE IF NOT EXISTS corpus_jobs (
 id TEXT PRIMARY KEY, book_id TEXT NOT NULL REFERENCES staging_books(id), kind TEXT NOT NULL,
 status TEXT NOT NULL, control TEXT NOT NULL DEFAULT '', phase TEXT NOT NULL,
 source_sha256 TEXT NOT NULL, base_version INTEGER NOT NULL, options_json TEXT NOT NULL,
 runtime_json TEXT NOT NULL, state_json TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
 original_book_status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS corpus_calls (
 job_id TEXT NOT NULL REFERENCES corpus_jobs(id), seq INTEGER NOT NULL, call_key TEXT NOT NULL,
 phase TEXT NOT NULL, status TEXT NOT NULL, request_sha256 TEXT NOT NULL,
 input_path TEXT NOT NULL, output_path TEXT NOT NULL, result_json TEXT,
 error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(job_id,seq));
CREATE INDEX IF NOT EXISTS corpus_call_key ON corpus_calls(job_id,call_key,seq);
CREATE TABLE IF NOT EXISTS corpus_method_origins (
 method_id TEXT NOT NULL, method_version INTEGER NOT NULL, book_id TEXT NOT NULL,
 structure_version INTEGER NOT NULL, basis_json TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(method_id,method_version),
 FOREIGN KEY(method_id,method_version) REFERENCES production_method_versions(method_id,version),
 FOREIGN KEY(book_id,structure_version) REFERENCES corpus_structure_versions(book_id,version));
'''
