"""Structured-method persistence, review, provenance and additive legacy migration."""
from copy import deepcopy
import json
import sqlite3

import pytest

from nw.materials.phase_contract import FIELDS
from nw.materials.phase_routes import ORDER
from nw.studio import catalog
from nw.studio.library import LibraryService
from nw.studio.method_contract import SECTIONS
from nw.studio.method_migration import migrate_legacy
from nw.studio.production_inputs import STAGES

SOURCE = '[FAKE] 隔离参考文件😀\n# 第一章\n  测试前因与已知信息。\n# 第二章\n测试选择与后果。\n'


@pytest.fixture
def library(tmp_path):
    return LibraryService(tmp_path / 'isolated')


def reference(library, *, decompose=False):
    book = library.import_book({'title': '[FAKE] 方法证据测试', 'filename': 'reference.md', 'text': SOURCE})
    if book['status'] == 'pending_review':
        book = library.review_book(book['id'], {'types': ['GENRE_XUANYI'], 'decompose': decompose})
    return book


def method_body(library):
    book = reference(library)
    evidence = library.locate_method_evidence({'book_id': book['id'], 'quote': '测试前因与已知信息。',
                                              'explanation': '[FAKE] 仅测试证据定位，不是创作经验'})
    return {'title': '[FAKE] 问题接力测试', 'tasks': ['hook'], 'scopes': ['chapter'],
        'type_tags': ['GENRE_XUANYI'], 'applicability': ['[FAKE] 已有批准的本章事件与未决问题'],
        'prerequisites': [{'key': 'input_1', 'input_kind': 'accepted_state', 'artifact': '[FAKE] 上章未决问题',
                           'requirement': '[FAKE] 核对其实际结果和人物所知'}],
        'operations': [{'key': 'operation_1', 'instruction': '[FAKE] 以实际结果明确新的未决问题',
                        'input_keys': ['input_1'], 'output_keys': ['output_1']}],
        'outputs': [{'key': 'output_1', 'stage': 'plot_design', 'field': 'reader_plan',
                     'artifact_kind': 'stage_product', 'description': '[FAKE] 读者问题与披露顺序'}],
        'downstream': [{'output_key': 'output_1', 'consumer': 'scene_design', 'usage': '[FAKE] 交给场景确定允许披露'}],
        'acceptance': [{'output_key': 'output_1', 'check': '[FAKE] 问题能追到具体事件和回应',
                        'evidence_required': '[FAKE] 场景安排与对应正文位置'}],
        'evidence': [evidence], 'non_applicability': ['[FAKE] 前章结果和问题尚未批准时返回补设计']}


def save(library, body=None):
    return library.save_method({'body': body or method_body(library), 'expected_version': 0})


def approve(library, row):
    return library.review_method(row['id'], {'version': row['version'], 'decision': 'approve',
                                             'note': '[FAKE] 隔离测试，未进行文学评价'})


def test_task_catalog_uses_real_stages_products_and_one_legacy_mapping(library):
    result = library.method_catalog()
    assert len(result['tasks']) == 22
    narration = next(task for task in result['tasks'] if task['id'] == 'narration')
    assert set(narration['stages']) == {'expression_design', 'scene_design'}
    assert set().union(*(set(t['stages']) for t in result['tasks'])) == set(ORDER)
    assert set(result['scopes']) == {'book', 'volume', 'chapter', 'scene'}
    for stage in result['stages']:
        extra = {'character_design': {'cast_assignments'}, 'plot_design': {'cast_events','continuations'},
                 'scene_design': {'cast_payoffs','scene_progress'}}
        assert set(stage['output_fields']) == set(FIELDS[stage['id']]) | extra.get(stage['id'],set())
        assert set(stage['output_fields']) <= result['output_labels'].keys()
    assert STAGES is catalog.SLOT_STAGES
    assert STAGES['structure'] == ['plot_design', 'scene_design']
    assert STAGES['hook'] == ['plot_design', 'event_design']
    assert result['runtime_integration'] == 'project_design_and_review'


@pytest.mark.parametrize('section', SECTIONS)
def test_incomplete_method_remains_a_draft_and_cannot_be_approved(library, section):
    body = method_body(library)
    body[section] = []
    row = save(library, body)
    assert row['status'] == 'draft'
    assert any(i['field'] == section for i in row['issues'])
    with pytest.raises(ValueError, match='尚不能批准'):
        approve(library, row)
    assert library.list_methods(status='approved')['total'] == 0


def test_versioned_review_keeps_old_body_active_while_revision_is_pending(library):
    original = save(library)
    approved = approve(library, original)
    assert approved['available'] and approved['approved_version'] == 1
    body = deepcopy(approved['body'])
    body['title'] += '修订'
    latest = library.save_method({'body': body, 'expected_version': 1}, approved['id'])
    assert latest['version'] == 2 and latest['status'] == 'draft' and latest['approved_version'] == 1
    assert library.list_methods(status='approved')['methods'][0]['version'] == 1
    assert library.get_method(original['id'], 1)['body'] == original['body']
    with pytest.raises(ValueError, match='已更新'):
        library.save_method({'body': original['body'], 'expected_version': 1}, original['id'])
    with pytest.raises(ValueError, match='当前版本'):
        approve(library, original)
    approve(library, latest)
    reopened = LibraryService(library.workspace)
    assert reopened.list_methods(status='approved')['methods'][0]['version'] == 2
    assert len(reopened.get_method(original['id'])['history']) == 2
    assert reopened.get_method(original['id'], 1)['body_sha256'] == original['body_sha256']


def test_review_is_once_per_version_and_rejection_requires_a_new_revision(library):
    row = save(library)
    rejected = library.review_method(row['id'], {'version': 1, 'decision': 'reject', 'note': '[FAKE] 要求补核前置'})
    assert rejected['status'] == 'rejected' and not rejected['available']
    with pytest.raises(ValueError, match='已审核'):
        approve(library, row)
    new = library.save_method({'body': row['body'], 'expected_version': 1}, row['id'])
    assert approve(library, new)['version'] == 2


@pytest.mark.parametrize('change,field', [
    (lambda b: b['operations'][0].update(input_keys=['unknown']), 'operations'),
    (lambda b: b['operations'][0].update(output_keys=['unknown']), 'operations'),
    (lambda b: b['downstream'][0].update(consumer='type_selection'), 'downstream'),
    (lambda b: b['acceptance'][0].update(output_key='unknown'), 'outputs'),
    (lambda b: b.update(tasks=['expression']), 'outputs'),
    (lambda b: b.update(tasks=['main_plot']), 'scopes'),
    (lambda b: b['outputs'].append({**b['outputs'][0], 'key': 'output_2'}), 'outputs'),
])
def test_methods_cannot_pass_with_broken_input_output_or_scope_links(library, change, field):
    body = method_body(library)
    change(body)
    row = save(library, body)
    assert any(issue['field'] == field for issue in row['issues'])
    with pytest.raises(ValueError, match='尚不能批准'):
        approve(library, row)


@pytest.mark.parametrize('change', [
    lambda b: b['outputs'][0].update(field='invented_hook_card'),
    lambda b: b['prerequisites'][0].update(input_kind='unknown'),
    lambda b: b.update(authority='original_source'),
    lambda b: b['operations'][0].update(key='unsafe/path'),
    lambda b: b.update(scopes=['replan']),
    lambda b: b['outputs'][0].update(artifact_kind='character'),
])
def test_unknown_fields_and_invented_product_locations_are_rejected(library, change):
    body = method_body(library)
    change(body)
    with pytest.raises(ValueError):
        save(library, body)
    assert library.list_methods()['total'] == 0


def test_evidence_positions_preserve_whitespace_and_unicode_codepoints(library):
    body = method_body(library)
    quote = '  测试前因与已知信息。\n'
    evidence = library.locate_method_evidence({'book_id': body['evidence'][0]['book_id'], 'quote': quote,
                                              'explanation': '[FAKE] 保持空白与非 BMP 字符之前的位置'})
    assert evidence['start'] == SOURCE.index(quote)
    body['evidence'] = [evidence]
    row = approve(library, save(library, body))
    assert row['body']['evidence'][0]['quote'] == quote
    assert row['evidence_locations'][0]['chapters'] == ['# 第一章']
    assert row['evidence_locations'][0]['source_sha256']


def test_duplicate_quote_requires_an_explicit_source_position(library):
    book = reference(library)
    with pytest.raises(ValueError, match='多次'):
        library.locate_method_evidence({'book_id': book['id'], 'quote': '测试'})
    evidence = library.locate_method_evidence({'book_id': book['id'], 'quote': '测试', 'start': SOURCE.rindex('测试')})
    assert evidence['end'] == SOURCE.rindex('测试') + 2


def test_invalid_evidence_is_atomic_and_never_becomes_a_method(library):
    body = method_body(library)
    body['evidence'][0]['quote'] = '[FAKE] 幻觉证据'
    with pytest.raises(ValueError, match='定位不一致'):
        save(library, body)
    assert library.list_methods()['total'] == 0


@pytest.mark.parametrize('withdraw', [False, True])
def test_changed_or_withdrawn_source_removes_live_availability_but_keeps_history(library, withdraw):
    row = approve(library, save(library))
    book_id = row['body']['evidence'][0]['book_id']
    if withdraw:
        library.review_book(book_id, {'decision': 'reject', 'note': '[FAKE] 撤回来源'})
    else:
        source = library._staging_row(book_id)
        (library.root / source['file_path']).write_text('[FAKE] 外部变更', encoding='utf-8')
    assert library.list_methods(status='approved')['total'] == 0
    current = library.get_method(row['id'], 1)
    assert current['status'] == 'source_unavailable' and current['source_issues']
    assert current['body_sha256'] == row['body_sha256']


def test_source_not_yet_archived_cannot_be_approved(library):
    body = method_body(library)
    with library.connect() as conn:
        conn.execute("UPDATE staging_books SET status='pending_verify' WHERE id=?", (body['evidence'][0]['book_id'],))
    row = save(library, body)
    with pytest.raises(ValueError, match='尚未审核入库'):
        approve(library, row)


def test_legacy_migration_is_additive_idempotent_and_does_not_promote_old_approval(library):
    book = reference(library, decompose=True)
    quote = '测试前因与已知信息。'
    option = next(k for k, value in catalog.option_map('hook').items() if value.get('selectable') is not False)
    book = library.decompose_book(book['id'], {'items': [{'slot': 'hook', 'option_key': option,
        'usage_text': '[FAKE] 旧用法短文', 'evidence': {'quote': quote}}]})
    library.verify_book(book['id'], {'approve_all': True})
    with library.connect() as conn:
        before = [dict(r) for r in conn.execute('SELECT * FROM decomp_items')]
        upgrades = [dict(r) for r in conn.execute('SELECT * FROM upgrade_candidates')]
    assert migrate_legacy(library) == 0
    reopened = LibraryService(library.workspace)
    with reopened.connect() as conn:
        assert [dict(r) for r in conn.execute('SELECT * FROM decomp_items')] == before
        assert [dict(r) for r in conn.execute('SELECT * FROM upgrade_candidates')] == upgrades
    result = reopened.list_methods()
    assert result['total'] == result['legacy_pending_count'] == 1
    row = result['methods'][0]
    assert row['status'] == 'draft' and row['approved_version'] is None
    assert row['body']['tasks'] == row['body']['scopes'] == []
    assert row['legacy']['usage_text'] == before[0]['usage_text']
    assert row['origin_item_id'] == before[0]['id'] and row['issues']
    assert reopened.list_methods(status='approved')['methods'] == []


def test_filtering_uses_task_scope_and_all_requested_type_tags(library):
    row = approve(library, save(library))
    assert library.list_methods(task='hook', scope='chapter', types=['GENRE_XUANYI'])['total'] == 1
    assert library.list_methods(task='world_rules')['total'] == 0
    assert library.list_methods(scope='book')['total'] == 0
    assert library.list_methods(types=['GENRE_XUANHUAN'])['total'] == 0
    assert library.list_methods(q='问题接力')['methods'][0]['id'] == row['id']
    assert library.list_methods(limit=1, offset=1)['methods'] == []


def test_frozen_body_hash_detects_external_changes(library):
    row = save(library)
    with library.connect() as conn:
        body = deepcopy(row['body'])
        body['title'] = '[FAKE] 越过版本保存'
        conn.execute('UPDATE production_method_versions SET body_json=? WHERE method_id=?',
                     (json.dumps(body, ensure_ascii=False), row['id']))
    with pytest.raises(ValueError, match='完整性'):
        library.get_method(row['id'])


def test_sqlite_backup_preserves_methods_reviews_and_evidence(library, tmp_path):
    row = approve(library, save(library))
    target = tmp_path / 'method-backup.db'
    with library.connect() as source:
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
    with sqlite3.connect(target) as saved:
        assert saved.execute('SELECT body_sha256 FROM production_method_versions').fetchone()[0] == row['body_sha256']
        assert saved.execute('SELECT decision FROM production_method_reviews').fetchone()[0] == 'approve'


def test_expanded_parent_tags_roundtrip_without_truncation(library):
    body = method_body(library)
    children = [g['children'][0]['id'] for g in catalog.genres() if g['children']][:8]
    body['type_tags'] = children
    first = save(library, body)
    assert len(first['body']['type_tags']) == 16
    second = library.save_method({'body': first['body'], 'expected_version': 1}, first['id'])
    assert second['body']['type_tags'] == first['body']['type_tags']


def test_repository_snapshot_restores_method_versions_and_original_evidence(library, tmp_path):
    from nw.studio.repository_data import restore, snapshot
    row = approve(library, save(library))
    archive = tmp_path / 'git-runtime'
    frozen = snapshot(library.workspace, archive)
    assert {'library/library.db', 'library/imports/' + row['body']['evidence'][0]['book_id'] + '.txt'} <= {
        entry['path'] for entry in frozen['entries']}
    other = tmp_path / 'other-checkout'
    other.mkdir()
    restore(archive, other)
    restored = LibraryService(other).get_method(row['id'])
    assert restored['available']
    assert restored['body_sha256'] == row['body_sha256']
    assert restored['evidence_locations'] == row['evidence_locations']


def test_genuine_old_schema_adds_methods_without_rewriting_legacy_rows(tmp_path):
    import hashlib
    from nw.studio.library import SCHEMA
    from nw.studio.library_util import encode
    workspace = tmp_path / 'old-schema'
    root = workspace / 'library'
    (root / 'imports').mkdir(parents=True)
    source = root / 'imports/old.txt'
    source.write_text(SOURCE, encoding='utf-8')
    sha = hashlib.sha256(SOURCE.encode('utf-8')).hexdigest()
    option = next(k for k, v in catalog.option_map('hook').items() if v.get('selectable') is not False)
    quote = '测试选择与后果。'
    with sqlite3.connect(root / 'library.db') as db:
        db.executescript(SCHEMA)
        db.execute('INSERT INTO staging_books(id,title,file_path,sha256,words,filename,detected_types_json,'
            'confirmed_types_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            ('old-book', '[FAKE] 旧库', 'imports/old.txt', sha, len(SOURCE), 'old.txt', '[]',
             '["GENRE_XUANYI"]', 'archived', 'before', 'before'))
        evidence = {'quote': quote, 'start': SOURCE.index(quote), 'end': SOURCE.index(quote)+len(quote), 'source_sha256': sha}
        original = ('old-item', 'old-book', 'hook', option, '["GENRE_XUANYI"]', '["plot_design"]',
                    '[FAKE] 保留旧批准短文', encode(evidence), 'approved', 'before', 'before', 'manual')
        db.execute('INSERT INTO decomp_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', original)
    upgraded = LibraryService(workspace)
    with upgraded.connect() as db:
        assert tuple(db.execute('SELECT * FROM decomp_items').fetchone()) == original
        assert db.execute('SELECT version FROM method_schema').fetchone()[0] == 1
    row = upgraded.list_methods()['methods'][0]
    assert row['status'] == 'draft' and row['origin_item_id'] == 'old-item'
    assert row['body']['tasks'] == row['body']['scopes'] == []
    assert source.read_text(encoding='utf-8') == SOURCE


def test_concurrent_revision_has_one_winner_and_preserves_the_original(library):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    row = save(library)
    barrier = Barrier(2)

    def revise(suffix):
        body = deepcopy(row['body'])
        body['title'] += suffix
        barrier.wait(timeout=5)
        try:
            library.save_method({'body': body, 'expected_version': 1}, row['id'])
            return 'saved'
        except ValueError as exc:
            assert '已更新' in str(exc)
            return 'stale'

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(revise, ('A', 'B')))
    assert sorted(results) == ['saved', 'stale']
    assert len(library.get_method(row['id'])['history']) == 2
    assert library.get_method(row['id'], 1)['body_sha256'] == row['body_sha256']


def test_book_method_cannot_claim_an_output_from_a_stage_book_never_executes(library):
    body = method_body(library)
    body['scopes'] = ['book']
    body['outputs'][0].update(stage='event_design', field='candidates')
    row = save(library, body)
    assert any('范围不执行' in issue['message'] for issue in row['issues'])
    with pytest.raises(ValueError, match='范围不执行'):
        approve(library, row)
