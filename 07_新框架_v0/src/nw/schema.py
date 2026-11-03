"""SQLite schema and incremental migrations."""

VERSION = 5
MIGRATE_V4 = """
BEGIN IMMEDIATE;
CREATE TABLE ab_experiments(
 id TEXT PRIMARY KEY, scene_id TEXT NOT NULL REFERENCES scenes(id),
 mapping_json TEXT NOT NULL CHECK(json_valid(mapping_json)), seal TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('IN_PROGRESS','READY','BLOCKED')),
 choice INTEGER CHECK(choice IN (1,2)), revealed INTEGER NOT NULL DEFAULT 0 CHECK(revealed IN (0,1)),
 created_at TEXT NOT NULL);
PRAGMA user_version=4;
COMMIT;
"""
MIGRATE_V3 = '''
BEGIN IMMEDIATE;
CREATE TABLE flow_meta(scene_id TEXT PRIMARY KEY REFERENCES scenes(id),
 settings_json TEXT NOT NULL CHECK(json_valid(settings_json)),
 notes_json TEXT NOT NULL CHECK(json_valid(notes_json)));
CREATE TABLE flow_nodes(scene_id TEXT NOT NULL REFERENCES flow_meta(scene_id),
 node TEXT NOT NULL CHECK(node IN ('N1','N2','N3','N4','N5','N6')),
 status TEXT NOT NULL CHECK(status IN ('PLANNED','IN_PROGRESS','DONE','BLOCKED')),
 input_json TEXT NOT NULL CHECK(json_valid(input_json)),
 output_json TEXT NOT NULL CHECK(json_valid(output_json)), PRIMARY KEY(scene_id,node));
PRAGMA user_version=3;
COMMIT;
'''
MIGRATE_V2 = '''
BEGIN IMMEDIATE;
CREATE TABLE run_outputs(run_id TEXT PRIMARY KEY REFERENCES runs(id),
 request_id TEXT, raw_json TEXT NOT NULL CHECK(json_valid(raw_json)));
PRAGMA user_version=2;
COMMIT;
'''
SCHEMA = '''
BEGIN IMMEDIATE;
CREATE TABLE projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE briefs(
 project_id TEXT NOT NULL REFERENCES projects(id), text TEXT NOT NULL,
 constraints TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
 PRIMARY KEY(project_id,version));
CREATE TABLE bible_entries(
 project_id TEXT NOT NULL REFERENCES projects(id),
 kind TEXT NOT NULL CHECK(kind IN ('world','character','style','taboo')),
 name TEXT NOT NULL, body TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0),
 PRIMARY KEY(project_id,kind,name,version));
CREATE TABLE chapters(
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 "index" INTEGER NOT NULL CHECK("index">0), title TEXT NOT NULL,
 UNIQUE(project_id,"index"));
CREATE TABLE scenes(
 id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL REFERENCES chapters(id),
 "index" INTEGER NOT NULL CHECK("index">0), card_json TEXT NOT NULL CHECK(json_valid(card_json)),
 UNIQUE(chapter_id,"index"));
CREATE TABLE runs(
 id TEXT PRIMARY KEY, scene_id TEXT NOT NULL REFERENCES scenes(id),
 kind TEXT NOT NULL CHECK(kind IN ('write','review','revise')),
 provider TEXT NOT NULL, model TEXT NOT NULL,
 params_json TEXT NOT NULL CHECK(json_valid(params_json)),
 input_snapshot_json TEXT NOT NULL CHECK(json_valid(input_snapshot_json)),
 context_package_json TEXT NOT NULL CHECK(json_valid(context_package_json)),
 output_text TEXT NOT NULL, finish_reason TEXT NOT NULL,
 usage_json TEXT NOT NULL CHECK(json_valid(usage_json)),
 started_at TEXT NOT NULL, ended_at TEXT NOT NULL, UNIQUE(id,scene_id));
CREATE TABLE drafts(
 id TEXT PRIMARY KEY, scene_id TEXT NOT NULL REFERENCES scenes(id),
 version INTEGER NOT NULL CHECK(version>0), text TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('partial','complete','truncated','error')),
 run_id TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(scene_id,version), UNIQUE(id,scene_id),
 FOREIGN KEY(run_id,scene_id) REFERENCES runs(id,scene_id));
CREATE TABLE accepted(
 scene_id TEXT PRIMARY KEY REFERENCES scenes(id), draft_id TEXT NOT NULL,
 accepted_at TEXT NOT NULL,
 FOREIGN KEY(draft_id,scene_id) REFERENCES drafts(id,scene_id));
CREATE TABLE state_notes(
 scene_id TEXT NOT NULL REFERENCES scenes(id),
 kind TEXT NOT NULL CHECK(kind IN ('character_state','foreshadow','fact')), text TEXT NOT NULL);
CREATE TRIGGER draft_no_update BEFORE UPDATE ON drafts
 BEGIN SELECT RAISE(ABORT,'drafts are immutable'); END;
CREATE TRIGGER draft_no_delete BEFORE DELETE ON drafts
 BEGIN SELECT RAISE(ABORT,'drafts are immutable'); END;
CREATE TRIGGER draft_next_version BEFORE INSERT ON drafts
 WHEN NEW.version != (SELECT COALESCE(MAX(version),0)+1 FROM drafts WHERE scene_id=NEW.scene_id)
 BEGIN SELECT RAISE(ABORT,'draft version must be consecutive'); END;
CREATE TRIGGER accepted_complete_insert BEFORE INSERT ON accepted
 WHEN NOT EXISTS(SELECT 1 FROM drafts d JOIN runs r ON r.id=d.run_id
 WHERE d.id=NEW.draft_id AND d.scene_id=NEW.scene_id
 AND d.status='complete' AND r.finish_reason='complete')
 BEGIN SELECT RAISE(ABORT,'accepted requires complete draft and run'); END;
CREATE TRIGGER accepted_complete_update BEFORE UPDATE ON accepted
 WHEN NOT EXISTS(SELECT 1 FROM drafts d JOIN runs r ON r.id=d.run_id
 WHERE d.id=NEW.draft_id AND d.scene_id=NEW.scene_id
 AND d.status='complete' AND r.finish_reason='complete')
 BEGIN SELECT RAISE(ABORT,'accepted requires complete draft and run'); END;
PRAGMA user_version=1;
COMMIT;
'''

MIGRATE_V5 = """
BEGIN IMMEDIATE;
CREATE TABLE input_manifests(
 id TEXT PRIMARY KEY, payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
 package_json TEXT NOT NULL CHECK(json_valid(package_json)), sha256 TEXT NOT NULL);
CREATE TRIGGER input_manifests_no_update BEFORE UPDATE ON input_manifests
 BEGIN SELECT RAISE(ABORT,'input manifests are immutable'); END;
CREATE TRIGGER input_manifests_no_delete BEFORE DELETE ON input_manifests
 BEGIN SELECT RAISE(ABORT,'input manifests are immutable'); END;
CREATE TABLE budgets(
 id TEXT PRIMARY KEY, limits_json TEXT NOT NULL CHECK(json_valid(limits_json)),
 used_calls INTEGER NOT NULL DEFAULT 0 CHECK(used_calls>=0),
 reserved_calls INTEGER NOT NULL DEFAULT 0 CHECK(reserved_calls>=0),
 reserved_cost TEXT NOT NULL DEFAULT '0', spent_cost TEXT NOT NULL DEFAULT '0');
CREATE TABLE task_calls(
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 kind TEXT NOT NULL CHECK(kind IN ('plan','rule_extract','select','state_extract','fact_review')),
 manifest_id TEXT NOT NULL REFERENCES input_manifests(id),
 manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)),
 request_json TEXT NOT NULL CHECK(json_valid(request_json)),
 messages_json TEXT NOT NULL CHECK(json_valid(messages_json)),
 budget_id TEXT NOT NULL REFERENCES budgets(id),
 root_id TEXT NOT NULL REFERENCES task_calls(id),
 attempt INTEGER NOT NULL CHECK(attempt>0), retry_of TEXT UNIQUE REFERENCES task_calls(id),
 status TEXT NOT NULL CHECK(status IN ('STARTED','UNKNOWN','FINISHED')),
 output_text_json TEXT NOT NULL DEFAULT '""' CHECK(json_valid(output_text_json)),
 raw_json TEXT NOT NULL DEFAULT 'null' CHECK(json_valid(raw_json)),
 finish_reason TEXT CHECK(finish_reason IN ('complete','truncated','error','refused')),
 validation TEXT NOT NULL DEFAULT 'UNREVIEWED' CHECK(validation IN ('VALID','INVALID','UNREVIEWED')),
 result_json TEXT NOT NULL DEFAULT 'null' CHECK(json_valid(result_json)),
 request_id_json TEXT NOT NULL DEFAULT 'null' CHECK(json_valid(request_id_json)),
 usage_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(usage_json)),
 reason TEXT, started_at TEXT NOT NULL, ended_at TEXT);
CREATE TABLE call_reservations(
 id TEXT PRIMARY KEY, budget_id TEXT REFERENCES budgets(id),
 call_kind TEXT NOT NULL CHECK(call_kind IN ('run','task')), call_id TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('STARTED','UNKNOWN','FINISHED')),
 estimate_json TEXT NOT NULL CHECK(json_valid(estimate_json)),
 actual_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(actual_json)), UNIQUE(call_kind,call_id));
PRAGMA user_version=5;
COMMIT;
"""

MIGRATIONS = {0: SCHEMA, 1: MIGRATE_V2, 2: MIGRATE_V3, 3: MIGRATE_V4, 4: MIGRATE_V5}
