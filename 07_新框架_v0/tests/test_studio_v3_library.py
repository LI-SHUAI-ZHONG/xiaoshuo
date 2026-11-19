"""Studio v3 evidence, recommendation and independent upgrade contracts."""
from pathlib import Path
import json
from types import SimpleNamespace

import pytest

from nw.config import ConfigRequired
from nw.llm.base import GenResult
from nw.studio import catalog
from nw.studio.library import LibraryService
from nw.studio.staging_model import _run


@pytest.fixture
def library(tmp_path: Path) -> LibraryService:
    return LibraryService(tmp_path / 'workspace')


def imported(library: LibraryService, label: str = '一', types: list[str] | None = None) -> dict:
    book = library.import_book({'title': '测试书' + label, 'filename': label + '.txt',
                                'text': f'第一章 {label}\n雨水击打窗棂。他一言不发。她终于笑了。'})
    return library.review_book(book['id'], {'types': types or ['SUB_XUANHUAN_01'], 'grade': 'A'})


def usage(key: str = 'tone.TONE_COLD', quote: str = '他一言不发。') -> dict:
    return {'slot': 'tone', 'option_key': key, 'usage_text': '以短句和沉默保持语气克制',
            'stages': ['expression_design'], 'evidence': {'quote': quote}}


def archived(library: LibraryService, label: str, keys: list[str], types: list[str] | None = None) -> dict:
    book = imported(library, label, types)
    book = library.decompose_book(book['id'], {'items': [usage(key) for key in keys]})
    return library.verify_book(book['id'], {'approve_all': True})


def test_catalog_uses_real_counts_and_option_ids(library: LibraryService) -> None:
    result = library.genres()
    assert result['counts'] == {'main': 35, 'sub': 425}
    assert len(result['slots']) == 8
    assert all(r['color'].startswith('#') and len(r['color']) == 7 for r in result['genres'])
    xuanhuan = next(r for r in result['genres'] if r['id'] == 'GENRE_XUANHUAN')
    assert xuanhuan['children'][0]['id'] == 'SUB_XUANHUAN_01'
    assert xuanhuan['coverage'] == 0
    assert any(r['status'] == 'blocked' for r in result['combinations'])
    groups = library.options('tone')['options']
    assert groups[0]['selectable'] is False
    child = library.options('tone', groups[0]['key'])['options'][0]
    assert child['key'] == 'tone.TONE_SERIOUS'
    assert child['source_ref']['original_line'] == 20151


def test_no_corpus_has_three_blanks_even_with_original_materials(library: LibraryService) -> None:
    for slot in catalog.SLOTS:
        assert library.recommend(slot, ['SUB_XUANHUAN_01'])['recommendations'] == [None, None, None]


def test_duplicate_book_content_cannot_inflate_counts(library: LibraryService) -> None:
    one = library.import_book({'title': '一', 'filename': 'a.txt', 'text': '重复内容'})
    duplicate = library.import_book({'title': '二', 'filename': 'b.md', 'text': '重复内容'})
    assert one['id'] == duplicate['id'] and duplicate['duplicate'] is True
    assert len(library.list_staging()['books']) == 1


def test_review_can_archive_without_decomposing_or_recommendations(library: LibraryService) -> None:
    book = library.import_book({'filename': 'n.txt', 'text': '只作收藏，不拆解。'})
    result = library.review_book(book['id'], {'types': ['GENRE_XUANHUAN'], 'grade': 'A', 'decompose': False})
    assert result['status'] == 'archived' and result['decomposition_requested'] is False
    assert library.get_staging(book['id'])['items'] == []
    assert library.recommend('genre', [])['recommendations'] == [None, None, None]
    assert library.upgrades()['upgrades'] == []
    reopened = LibraryService(library.workspace)
    assert reopened.get_staging(book['id'])['decomposition_requested'] is False


def test_manual_evidence_closed_loop_and_per_book_dedup(library: LibraryService) -> None:
    one = archived(library, '一', ['tone.TONE_COLD', 'tone.TONE_COLD'])
    archived(library, '二', ['tone.TONE_COLD'])
    result = library.recommend('tone', ['SUB_XUANHUAN_01'])['recommendations']
    assert one['status'] == 'archived'
    assert result[0]['corpus_count'] == 2
    assert len(result[0]['books']) == 2 and len(result[0]['examples']) == 2
    assert result[1:] == [None, None]
    assert len(library.items('tone')['items']) == 3


def test_partial_approval_is_not_counted_until_book_archived(library: LibraryService) -> None:
    book = imported(library)
    book = library.decompose_book(book['id'], {'items': [usage(), usage('tone.TONE_WARM')]})
    book = library.verify_book(book['id'], {'approvals': [book['items'][0]['id']]})
    assert book['status'] == 'pending_verify'
    assert library.recommend('tone', [])['recommendations'] == [None, None, None]
    pending = next(i['id'] for i in book['items'] if i['status'] == 'draft')
    library.verify_book(book['id'], {'discards': [pending]})
    assert library.recommend('tone', [])['recommendations'][0]['corpus_count'] == 1


def test_three_tier_fallback_keeps_exact_first(library: LibraryService) -> None:
    archived(library, '精确', ['tone.TONE_COLD'], ['SUB_XUANHUAN_01', 'GENRE_XUANYI'])
    archived(library, '子类一', ['tone.TONE_WARM'], ['SUB_XUANHUAN_01'])
    archived(library, '子类二', ['tone.TONE_WARM'], ['SUB_XUANHUAN_01'])
    archived(library, '主类', ['tone.TONE_LIGHT'], ['SUB_XUANHUAN_02'])
    recs = library.recommend('tone', ['SUB_XUANHUAN_01', 'GENRE_XUANYI'])['recommendations']
    assert [r['level'] for r in recs] == ['exact', 'subgenre', 'main']
    assert [r['corpus_count'] for r in recs] == [1, 2, 1]


def test_adoption_only_with_review_ref_and_scene_dedup(library: LibraryService) -> None:
    archived(library, '一', ['tone.TONE_COLD', 'tone.TONE_WARM'])
    with pytest.raises(ValueError, match='审稿'):
        library.record_adoption('n1', 's1', ['tone.TONE_COLD'], '')
    library.record_adoption('n1', 's1', ['tone.TONE_COLD'], 'review-accepted')
    library.record_adoption('n1', 's1', ['tone.TONE_COLD'], 'review-accepted')
    rec = library.recommend('tone', [])['recommendations'][0]
    assert rec['option_key'] == 'tone.TONE_COLD' and rec['adopt_count'] == 1


@pytest.mark.parametrize('item', [usage(quote='原文不存在'), usage('tone.fabricated'),
                                 {**usage(), 'stages': ['nonexistent']},
                                 {**usage(), 'evidence': {'quote': '他一言不发。', 'start': 999}},
                                 {**usage(), 'evidence': {'quote': '他一言不发。', 'end': 999}}])
def test_invalid_decomposition_is_atomic(library: LibraryService, item: dict) -> None:
    book = imported(library)
    with pytest.raises(ValueError):
        library.decompose_book(book['id'], {'items': [usage(), item]})
    actual = library.get_staging(book['id'])
    assert actual['status'] == 'queued' and actual['items'] == []


def test_book_type_and_state_ownership(library: LibraryService) -> None:
    book = library.import_book({'filename': 'n.txt', 'text': '他一言不发。'})
    with pytest.raises(ValueError, match='状态'):
        library.decompose_book(book['id'], {'items': [usage()]})
    with pytest.raises(ValueError, match='未知类型'):
        library.review_book(book['id'], {'types': ['GENRE_FAKE']})
    first = imported(library, '一')
    second = imported(library, '二')
    first = library.decompose_book(first['id'], {'items': [usage()]})
    second = library.decompose_book(second['id'], {'items': [usage()]})
    with pytest.raises(ValueError, match='本书'):
        library.verify_book(first['id'], {'approvals': [second['items'][0]['id']]})


def test_imported_filename_never_controls_destination(library: LibraryService, tmp_path: Path) -> None:
    book = library.import_book({'filename': '../../escape.txt', 'text': '正文'})
    row = library._staging_row(book['id'])
    assert (library.root / row['file_path']).resolve().is_relative_to(library.root)
    assert not (tmp_path / 'escape.txt').exists()
    with pytest.raises(ValueError):
        library.import_book({'filename': 'unavailable.epub', 'text': '正文'})


def test_changed_source_blocks_approval(library: LibraryService) -> None:
    book = imported(library)
    book = library.decompose_book(book['id'], {'items': [usage()]})
    row = library._staging_row(book['id'])
    (library.root / row['file_path']).write_text('原文被改了', encoding='utf-8')
    with pytest.raises(ValueError, match='已改变'):
        library.verify_book(book['id'], {'approve_all': True})


def test_knowledge_feature_suggestions_are_observed_not_probabilities(library: LibraryService) -> None:
    assert library.get_type('GENRE_XUANHUAN')['features'] == []
    library.save_type('GENRE_XUANHUAN', {'features': ['修炼', '宗门'], 'definition': '作者维护定义'})
    book = library.import_book({'filename': 'n.txt', 'text': '他走入宗门，开始修炼。'})
    detection = book['detected_types'][0]
    assert detection['matched_features'] == ['修炼', '宗门']
    assert detection['confidence'] is None
    with pytest.raises(ValueError, match='已更新'):
        library.save_type('GENRE_XUANHUAN', {'version': 0, 'features': ['覆盖旧值']})


def test_frozen_references_are_selected_short_approved_and_bounded(library: LibraryService) -> None:
    for n in range(5):
        archived(library, str(n), ['tone.TONE_COLD', 'tone.TONE_WARM'])
    refs = library.freeze_references([{'option_key': 'tone.TONE_COLD'}], ['SUB_XUANHUAN_01'])
    assert len(refs) == 3 and len({r['book_id'] for r in refs}) == 3
    assert all(r['status'] == 'approved' and r['option_key'] == 'tone.TONE_COLD' for r in refs)
    assert all(len(r['evidence']['quote']) <= 400 for r in refs)


def test_upgrade_is_versioned_and_rejected_book_withdraws_live_sources(library: LibraryService) -> None:
    book = archived(library, '一', ['tone.TONE_COLD'])
    candidate = library.upgrades()['upgrades'][0]
    assert '候选待人工语义核对' in candidate['reason']
    assert library.approved_upgrades()['version'] == 0
    library.review_upgrade(candidate['id'], {'decision': 'approve'})
    frozen = library.approved_upgrades()
    assert frozen['version'] == 1 and len(frozen['items']) == 1
    library.review_book(book['id'], {'decision': 'reject'})
    assert library.recommend('tone', [])['recommendations'] == [None, None, None]
    assert library.approved_upgrades()['items'] == []
    assert len(frozen['items']) == 1  # independent historic snapshot is not rewritten


def test_automatic_decomposition_requires_real_configuration(library: LibraryService) -> None:
    book = imported(library)
    with pytest.raises(ConfigRequired, match='CONFIG_REQUIRED'):
        library.decompose_book(book['id'], {'mode': 'model'})
    assert library.get_staging(book['id'])['status'] == 'queued'


def test_upgrade_runtime_filters_book_type_but_keeps_version_index(library: LibraryService) -> None:
    archived(library, '玄幻', ['tone.TONE_COLD'], ['GENRE_XUANHUAN'])
    archived(library, '都市', ['tone.TONE_WARM'], ['GENRE_DUSHI'])
    for row in library.upgrades()['upgrades']:
        library.review_upgrade(row['id'], {'decision': 'approve'})
    snapshot = library.approved_upgrades(['SUB_XUANHUAN_01'])
    assert len(snapshot['items']) == 1
    assert snapshot['items'][0]['option_key'] == 'tone.TONE_COLD'
    assert snapshot['available_count'] == len(snapshot['index']) == 2
    assert snapshot['applicable_count'] == 1


def test_model_results_are_audited_and_still_require_author_approval(library: LibraryService) -> None:
    book = imported(library)
    with library.connect() as conn:
        conn.execute("UPDATE staging_books SET status='decomposing' WHERE id=?", (book['id'],))
    class TestProvider:
        def generate(self, messages: list, **params: dict) -> GenResult:
            item = {**usage(), 'usage_text': '[FAKE] 仅测试证据传输'}
            return GenResult(json.dumps({'items': [item]}, ensure_ascii=False), 'complete', {'tokens': 1}, 'test', {'test_only': True})
    cfg = SimpleNamespace(model='[FAKE] test-only', provider='test-only', params={})
    _run(library, book['id'], library.get_staging(book['id'])['text'], cfg, TestProvider())
    actual = library.get_staging(book['id'])
    assert actual['status'] == 'pending_verify' and actual['items'][0]['status'] == 'draft'
    assert library.recommend('tone', [])['recommendations'] == [None, None, None]
    inputs = list((library.root / 'calls').rglob('*.input.json'))
    outputs = list((library.root / 'calls').rglob('*.output.json'))
    assert len(inputs) == len(outputs) == 1
    assert json.loads(inputs[0].read_text(encoding='utf-8'))['messages'][1]['content'].endswith(actual['text'])


def test_model_hallucinated_evidence_returns_to_queue_without_items(library: LibraryService) -> None:
    book = imported(library)
    with library.connect() as conn:
        conn.execute("UPDATE staging_books SET status='decomposing' WHERE id=?", (book['id'],))
    class TestProvider:
        def generate(self, messages: list, **params: dict) -> GenResult:
            return GenResult(json.dumps({'items': [usage(quote='[FAKE] 不在原文')]}), 'complete', {}, None, {})
    _run(library, book['id'], library.get_staging(book['id'])['text'],
         SimpleNamespace(model='[FAKE]', provider='test-only', params={}), TestProvider())
    actual = library.get_staging(book['id'])
    assert actual['status'] == 'queued' and actual['items'] == [] and actual['error']


def test_restart_recovers_abandoned_decomposition_but_preserves_progress(library: LibraryService) -> None:
    book = imported(library)
    with library.connect() as conn:
        conn.execute("UPDATE staging_books SET status='decomposing',progress=0.5 WHERE id=?", (book['id'],))
    reopened = LibraryService(library.workspace)
    result = reopened.get_staging(book['id'])
    assert result['status'] == 'queued' and result['progress'] == .5
    assert '中断' in result['error'] and result['items'] == []


def test_restart_does_not_recover_a_live_process_lock(library: LibraryService) -> None:
    from nw.call_control import execution_lock
    book = imported(library)
    with library.connect() as conn:
        conn.execute("UPDATE staging_books SET status='decomposing' WHERE id=?", (book['id'],))
    with execution_lock(SimpleNamespace(directory=library.root), f'decompose:{book["id"]}') as locked:
        assert locked
        reopened = LibraryService(library.workspace)
        assert reopened.get_staging(book['id'])['status'] == 'decomposing'


def test_model_failure_can_retry_with_new_audit_files(library: LibraryService, monkeypatch) -> None:
    import threading
    from nw.config import Config
    from nw.studio import staging_model

    book = imported(library)
    library.config_path = library.root / 'not-read-test-config.toml'
    config = Config('ollama', 'http://localhost', '[FAKE] isolated-adapter', '', 1, {}, library.workspace)
    release, started = threading.Event(), threading.Event()
    class TestProvider:
        name = 'ollama'
        complete = False
        def generate(self, messages: list, **params: dict) -> GenResult:
            started.set()
            release.wait(timeout=5)
            if not self.complete:
                return GenResult('[FAKE] truncated', 'truncated', {}, 'test', {'isolated_test': True})
            item = {**usage(), 'usage_text': '[FAKE] retry evidence'}
            return GenResult(json.dumps({'items': [item]}, ensure_ascii=False), 'complete', {}, 'test', {'isolated_test': True})
    provider = TestProvider()
    monkeypatch.setattr(staging_model, 'load_config', lambda path: config)
    monkeypatch.setattr(staging_model, 'make_provider', lambda cfg: provider)
    first = library.decompose_book(book['id'], {})
    assert first['status'] == 'decomposing' and first['progress'] == 0
    assert started.wait(timeout=5)
    worker = library._tasks[book['id']]
    release.set()
    worker.join(timeout=5)
    assert library.get_staging(book['id'])['status'] == 'queued'
    provider.complete = True
    started.clear()
    release.clear()
    library.decompose_book(book['id'], {})
    assert started.wait(timeout=5)
    worker = library._tasks[book['id']]
    release.set()
    worker.join(timeout=5)
    actual = library.get_staging(book['id'])
    assert actual['status'] == 'pending_verify' and actual['progress'] == 1
    assert actual['items'][0]['status'] == 'draft'
    assert len(list((library.root / 'calls').rglob('*.input.json'))) == 2
    assert len(list((library.root / 'calls').rglob('*.output.json'))) == 2
