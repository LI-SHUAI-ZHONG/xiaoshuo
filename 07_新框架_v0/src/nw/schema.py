"""SQLite schema and incremental migrations."""

VERSION = 11
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

MIGRATE_V6 = """
BEGIN IMMEDIATE;
CREATE TABLE source_versions(
 id TEXT PRIMARY KEY, relative_path TEXT NOT NULL, file_sha256 TEXT NOT NULL CHECK(length(file_sha256)=64),
 byte_size INTEGER NOT NULL CHECK(byte_size>=0), encoding TEXT,
 status TEXT NOT NULL CHECK(status IN ('READY','NUL','INVALID_ENCODING','EMPTY')),
 UNIQUE(relative_path,file_sha256));
CREATE TABLE source_spans(
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source_versions(id),
 start_line INTEGER NOT NULL CHECK(start_line>=1), end_line INTEGER NOT NULL CHECK(end_line>=start_line),
 span_sha256 TEXT NOT NULL CHECK(length(span_sha256)=64), text TEXT NOT NULL CHECK(length(text)>0),
 UNIQUE(source_id,start_line,end_line));
CREATE TRIGGER source_spans_ready BEFORE INSERT ON source_spans
 WHEN (SELECT status FROM source_versions WHERE id=NEW.source_id) != 'READY'
 BEGIN SELECT RAISE(ABORT,'quarantined source'); END;
CREATE TABLE cards(
 card_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>=1),
 kind TEXT NOT NULL CHECK(kind IN ('world','character','style','taboo','plot','scene','promise',
                                  'rule','brief','volume','chapter')),
 origin TEXT NOT NULL CHECK(origin IN ('repository','author','model')),
 body_json TEXT NOT NULL CHECK(json_valid(body_json) AND json_type(body_json)='object'),
 source_refs_json TEXT NOT NULL CHECK(json_valid(source_refs_json) AND json_type(source_refs_json)='array'),
 created_at TEXT NOT NULL, PRIMARY KEY(card_id,version));
CREATE TRIGGER cards_consecutive BEFORE INSERT ON cards
 WHEN NEW.version != (SELECT COALESCE(MAX(version),0)+1 FROM cards WHERE card_id=NEW.card_id)
 BEGIN SELECT RAISE(ABORT,'card versions must be consecutive'); END;
CREATE TABLE card_decisions(
 id TEXT PRIMARY KEY, card_id TEXT NOT NULL, version INTEGER NOT NULL,
 decision TEXT NOT NULL CHECK(decision IN ('trial','approved','disabled')),
 reason TEXT NOT NULL CHECK(length(trim(reason))>0), created_at TEXT NOT NULL,
 FOREIGN KEY(card_id,version) REFERENCES cards(card_id,version));
CREATE INDEX card_decisions_card ON card_decisions(card_id,version);
CREATE TABLE card_links(
 id TEXT PRIMARY KEY, from_card_id TEXT NOT NULL, from_version INTEGER NOT NULL,
 to_card_id TEXT NOT NULL, to_version INTEGER NOT NULL,
 relation TEXT NOT NULL CHECK(relation IN ('interprets','corrects','contradicts','depends_on','contains','supersedes')),
 FOREIGN KEY(from_card_id,from_version) REFERENCES cards(card_id,version),
 FOREIGN KEY(to_card_id,to_version) REFERENCES cards(card_id,version),
 UNIQUE(from_card_id,from_version,to_card_id,to_version,relation));
CREATE TABLE plan_applications(
 proposal_id TEXT PRIMARY KEY REFERENCES task_calls(id), decision_id TEXT NOT NULL REFERENCES card_decisions(id),
 mapping_json TEXT NOT NULL CHECK(json_valid(mapping_json)));
""" + ''.join(
    f"""CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table}
 BEGIN SELECT RAISE(ABORT,'{table} is append-only'); END;
"""
    for table in ('source_versions', 'source_spans', 'cards', 'card_decisions', 'card_links')
    for action in ('UPDATE', 'DELETE')
) + """PRAGMA user_version=6;
COMMIT;
"""

MIGRATE_V7 = """
BEGIN IMMEDIATE;
CREATE TABLE story_branches(
 id TEXT PRIMARY KEY, parent_branch_id TEXT REFERENCES story_branches(id),
 base_revision INTEGER NOT NULL, parent_at_fork INTEGER NOT NULL, head_revision INTEGER NOT NULL,
 enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
 baseline_json TEXT NOT NULL CHECK(json_valid(baseline_json)));
CREATE TABLE story_commits(
 id TEXT PRIMARY KEY, branch_id TEXT NOT NULL REFERENCES story_branches(id),
 revision INTEGER NOT NULL, base_revision INTEGER NOT NULL, payload_hash TEXT NOT NULL,
 state_json TEXT NOT NULL CHECK(json_valid(state_json)), created_at TEXT NOT NULL,
 UNIQUE(branch_id,revision));
CREATE TABLE state_deltas(
 id TEXT PRIMARY KEY, branch_id TEXT NOT NULL REFERENCES story_branches(id),
 base_revision INTEGER NOT NULL, draft_id TEXT NOT NULL REFERENCES drafts(id),
 manifest_id TEXT NOT NULL REFERENCES input_manifests(id),
 manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json)),
 operations_json TEXT NOT NULL CHECK(json_valid(operations_json)),
 validation_json TEXT NOT NULL CHECK(json_valid(validation_json)), sha256 TEXT NOT NULL,
 FOREIGN KEY(branch_id,base_revision) REFERENCES story_commits(branch_id,revision));
CREATE TABLE story_events(
 id TEXT PRIMARY KEY, commit_id TEXT NOT NULL REFERENCES story_commits(id),
 scene_id TEXT NOT NULL REFERENCES scenes(id), draft_id TEXT NOT NULL,
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
 FOREIGN KEY(draft_id,scene_id) REFERENCES drafts(id,scene_id));
CREATE TABLE story_slots(
 branch_id TEXT NOT NULL REFERENCES story_branches(id), scene_id TEXT NOT NULL REFERENCES scenes(id),
 draft_id TEXT NOT NULL, commit_id TEXT NOT NULL REFERENCES story_commits(id),
 delta_id TEXT REFERENCES state_deltas(id), PRIMARY KEY(branch_id,scene_id),
 FOREIGN KEY(draft_id,scene_id) REFERENCES drafts(id,scene_id));
CREATE TABLE story_decisions(
 id TEXT PRIMARY KEY, action TEXT NOT NULL CHECK(action IN ('adopt','accept','promote','settings','abandon')),
 targets_json TEXT NOT NULL CHECK(json_valid(targets_json)), reason TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE artifact_dependencies(
 consumer_kind TEXT NOT NULL, consumer_id TEXT NOT NULL, consumer_version INTEGER NOT NULL,
 consumer_sha256 TEXT NOT NULL, producer_kind TEXT NOT NULL, producer_id TEXT NOT NULL,
 producer_version INTEGER NOT NULL, producer_sha256 TEXT NOT NULL,
 PRIMARY KEY(consumer_kind,consumer_id,consumer_version,producer_kind,producer_id,producer_version));
CREATE INDEX artifact_dependencies_producer ON artifact_dependencies(producer_kind,producer_id,producer_version);
CREATE TABLE story_invalidations(
 producer_kind TEXT NOT NULL, producer_id TEXT NOT NULL, producer_version INTEGER NOT NULL,
 producer_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(producer_kind,producer_id,producer_version));
""" + ''.join(
    f"""CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table}
 BEGIN SELECT RAISE(ABORT,'{table} is append-only'); END;
"""
    for table in ('story_commits', 'state_deltas', 'story_events', 'story_decisions', 'artifact_dependencies',
                  'story_invalidations')
    for action in ('UPDATE', 'DELETE')
) + """PRAGMA user_version=7;
COMMIT;
"""

MIGRATE_V8 = """
BEGIN IMMEDIATE;
CREATE TABLE novel_jobs(
 id TEXT PRIMARY KEY, branch_id TEXT NOT NULL REFERENCES story_branches(id),
 request_json TEXT NOT NULL CHECK(json_valid(request_json)), budget_id TEXT NOT NULL REFERENCES budgets(id),
 status TEXT NOT NULL CHECK(status IN ('READY','RUNNING','WAITING','BLOCKED','STALE','REJECTED','CANCELLED','DONE')),
 step_key TEXT, reason TEXT, model_json TEXT CHECK(model_json IS NULL OR json_valid(model_json)),
 output_json TEXT NOT NULL CHECK(json_valid(output_json)));
CREATE TABLE novel_steps(
 job_id TEXT NOT NULL REFERENCES novel_jobs(id), step_key TEXT NOT NULL,
 attempt INTEGER NOT NULL CHECK(attempt>0), status TEXT NOT NULL CHECK(status IN ('STARTED','DONE','FAILED','STALE')),
 input_json TEXT NOT NULL CHECK(json_valid(input_json)), output_json TEXT NOT NULL CHECK(json_valid(output_json)),
 PRIMARY KEY(job_id,step_key,attempt));
ALTER TABLE story_decisions RENAME TO story_decisions_v7;
CREATE TABLE story_decisions(
 id TEXT PRIMARY KEY, action TEXT NOT NULL CHECK(action IN ('adopt','accept','promote','settings','abandon',
 'novel_confirm','novel_core','novel_reject','novel_review')),
 targets_json TEXT NOT NULL CHECK(json_valid(targets_json)), reason TEXT NOT NULL, created_at TEXT NOT NULL);
INSERT INTO story_decisions SELECT * FROM story_decisions_v7 ORDER BY rowid;
DROP TABLE story_decisions_v7;
""" + ''.join(
    f"""CREATE TRIGGER story_decisions_no_{action.lower()} BEFORE {action} ON story_decisions
 BEGIN SELECT RAISE(ABORT,'story_decisions is append-only'); END;
"""
    for action in ('UPDATE', 'DELETE')
) + """PRAGMA user_version=8;
COMMIT;
"""

def _task_kind_migration(old: int, new: int, kinds: str) -> str:
    calls = MIGRATE_V5.split('CREATE TABLE task_calls(', 1)[1].split('CREATE TABLE call_reservations(', 1)[0]
    calls = calls.replace("'fact_review'", f"'fact_review',{kinds}")
    return f"""
BEGIN IMMEDIATE;
ALTER TABLE plan_applications RENAME TO plan_applications_v{old};
ALTER TABLE task_calls RENAME TO task_calls_v{old};
CREATE TABLE task_calls({calls}
INSERT INTO task_calls SELECT * FROM task_calls_v{old} ORDER BY rowid;
CREATE TABLE plan_applications(
 proposal_id TEXT PRIMARY KEY REFERENCES task_calls(id), decision_id TEXT NOT NULL REFERENCES card_decisions(id),
 mapping_json TEXT NOT NULL CHECK(json_valid(mapping_json)));
INSERT INTO plan_applications SELECT * FROM plan_applications_v{old} ORDER BY rowid;
DROP TABLE plan_applications_v{old};
DROP TABLE task_calls_v{old};
PRAGMA user_version={new};
COMMIT;
"""


MIGRATE_V9 = _task_kind_migration(8, 9, "'material_work'")

MIGRATE_V10 = """
BEGIN IMMEDIATE;
CREATE TABLE chapter_records(
 id TEXT PRIMARY KEY,
 branch_id TEXT NOT NULL REFERENCES story_branches(id),
 chapter_id TEXT NOT NULL REFERENCES chapters(id),
 kind TEXT NOT NULL CHECK(kind IN ('summary','character','cost','commitment','commitment-ending',
                                   'resource-update','resource-inventory','resource-settlement')),
 input_sha256 TEXT NOT NULL,
 report_json TEXT NOT NULL CHECK(json_valid(report_json)), report_sha256 TEXT NOT NULL,
 created_at TEXT NOT NULL);
CREATE INDEX chapter_records_scope ON chapter_records(branch_id,chapter_id,kind,input_sha256);
CREATE TRIGGER chapter_records_no_update BEFORE UPDATE ON chapter_records
 BEGIN SELECT RAISE(ABORT,'chapter_records is append-only'); END;
CREATE TRIGGER chapter_records_no_delete BEFORE DELETE ON chapter_records
 BEGIN SELECT RAISE(ABORT,'chapter_records is append-only'); END;
PRAGMA user_version=10;
COMMIT;
"""

MIGRATE_V11 = _task_kind_migration(10, 11, "'material_work','book_directions'")

MIGRATIONS = {0: SCHEMA, 1: MIGRATE_V2, 2: MIGRATE_V3, 3: MIGRATE_V4, 4: MIGRATE_V5, 5: MIGRATE_V6,
              6: MIGRATE_V7, 7: MIGRATE_V8, 8: MIGRATE_V9, 9: MIGRATE_V10, 10: MIGRATE_V11}
