"""Scope material checks use complete chapter versions and gate atomic acceptance."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from nw.llm.base import GenResult
from nw.materials.adjudication import build_adjudications
from nw.materials.catalog import build_catalog, list_catalog
from nw.materials import library_adjudication
from nw.materials.route_catalog import route
from nw.materials.unit_catalog import index_units
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_catalog import _manifest
from test_material_workflow import choose
from test_novel_flow import Model, author, config


def source_pin(tmp_path, monkeypatch, kind='chapter', *, scene_length=False):
    text = ('### 91.1_整章场景检查\n【定义】每章包含两个目标清楚的场景。\n'
            '【指令】全章必须从进入调查推进到取得证据。\n'
            '【判定标准】整章有两个场景，各场目标与章末后果相连。\n')
    if kind != 'chapter':
        target = '不同章节' if kind == 'cross_chapter' else '全书各章'
        text = f'### 91.1_范围语言检查\n【定义】叙述保持贴近人物的语言。\n【指令】{target}必须保持贴近观察者。\n【判定标准】对照{target}的句式与叙述距离。\n'
    if scene_length:
        text = ('### 91.1_整章场景检查\n【定义】第三场长于前两场。\n'
                '【指令】第三场须分别大于第一、二场篇幅的1.2倍。\n'
                '【判定标准】用同一口径统计前三场字数。\n')
    data = text.encode()
    monkeypatch.setitem(library_adjudication._PINNED, 'library', sha256(data).hexdigest())
    mf = _manifest(tmp_path / 'sources', tmp_path, [('library.txt', 'library', data)])
    build_catalog(tmp_path, tmp_path / 'sources', mf)
    index_units(tmp_path, None)
    key = '91.1_整章场景检查' if kind == 'chapter' else '91.1_范围语言检查'
    root = list_catalog(tmp_path, None, key)['fragments'][0]
    if scene_length:
        monkeypatch.setitem(library_adjudication._SCOPED_LIBRARY_CHECKS, (key, root['sha256']),
                            {'kind': 'chapter', 'scene_indices': [1, 2, 3], 'metric': 'third_scene_length'})
    build_adjudications(tmp_path)
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)
    result = route(tmp_path, root['fragment_id'])
    assert result['profile'] == 'scope_review'
    return {**{key: result['source'][key] for key in ('id', 'sha256', 'file_sha256')},
            'disposition': 'required', 'reason': '检查真实整章而不是单场'}


def test_explicit_chapter_statistics_and_original_checklist_require_full_chapters(tmp_path, monkeypatch):
    from nw.materials.work_catalog import SourceDesk

    text = ('### 157.1_对话字数占比上限\n【定义】每章对话字数占总字数的比例上限。\n'
            '【调用条件】每章写作完成后统计。\n【指令】单章对话字数占比 ≤ 45%\n\n'
            '## 板块162 审美与板块的映射关系\n\n'
            '**162.2 审美检查清单**\n\n每章编辑模式检查：\n\n'
            '- [ ] 场景是否有空间结构和光线来源？\n- [ ] 关键动作是否有蓄力和结果？\n')
    data = text.encode('utf-8')
    monkeypatch.setitem(library_adjudication._PINNED, 'library', sha256(data).hexdigest())
    root = tmp_path / 'sources'
    build_catalog(tmp_path, root, _manifest(root, tmp_path, [('library.txt', 'library', data)]))
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    desk = SourceDesk(tmp_path)
    for key in ('157.1_对话字数占比上限', '162.2_审美检查清单'):
        ident, = [row['id'] for row in desk.rows if row['key'] == key]
        review = route(tmp_path, ident)['adjudication']
        assert review['profile'] == 'scope_review' and review['state'] == 'design_ready'
        assert review['contract']['evidence_scope'] == {'kind': 'chapter', 'complete_chapters_required': True,
                                                         'author_scope_required': True}
    checks = [row for row in review['contract']['obligations'] if row['kind'] == 'check']
    assert [row['text'] for row in checks] == ['场景是否有空间结构和光线来源？', '关键动作是否有蓄力和结果？']


class ScopeModel(Model):
    def __init__(self, failure='', kind='chapter', *, third_scene_chars=None):
        super().__init__()
        self.failure = failure
        self.kind = kind
        self.third_scene_chars = third_scene_chars
        self.written = 0

    def generate(self, messages, **params):
        prompt, data = messages[0]['content'], json.loads(messages[-1]['content'])
        if 'material_scope_review' in data:
            self.calls.append(messages)
            contract = data['material_scope_review']
            if self.third_scene_chars is None:
                assert len(contract['drafts']) == 2
            else:
                assert [entry['scene_index'] for entry in contract['drafts']] == [1, 2, 3]
                assert contract['checks'][0]['stage_metrics'] == {
                    'scene_character_counts': [15, 20, self.third_scene_chars]}
            spans = [{**entry['ref'], 'start': 7, 'end': len(entry['text']), 'quote': entry['text'][7:]}
                     for entry in contract['drafts']]
            if self.failure == 'one_chapter':
                spans = spans[:1]
            checks = []
            for check in contract['checks']:
                fields = [{'id': field['id'], 'status': 'pass', 'reason': '两场各有明确目标，并以行动取得印记证据',
                           'evidence': spans} for field in check['source_contract']['obligations']]
                if self.failure == 'omit':
                    fields.pop()
                if self.failure == 'old_hash':
                    fields[0]['evidence'] = [{**spans[0], 'sha256': 'a' * 64}]
                checks.append({'id': check['id'], 'status': 'failed' if self.failure == 'failed' else 'pass',
                               'reason': '比较两场目标和章末证据，因果顺序与原检查一致',
                               'evidence': spans, 'source_checks': fields})
            return GenResult(json.dumps({'recommendation': 'pass', 'notes': '逐稿检查整章',
                                         'material_checks': checks}, ensure_ascii=False), 'complete', {}, 'fake', {})
        if 'candidate_cards' in prompt:
            output = super().generate(messages, **params)
            raw = json.loads(output.text)
            if data['scope'] != 'book':
                row = data['materials'][0]
                ident = row['source']['id']
                fields = row['review']['contract']['obligations']
                for candidate in raw['candidate_cards']:
                    other = deepcopy(next(member for member in candidate['members'] if member['kind'] == 'scene'))
                    other['key'] = 'scene2'
                    other['body']['title'] = '辨认旧印'
                    candidate['members'].append(other)
                    if self.kind == 'chapter':
                        candidate['chapters'][0]['scenes'].append({'index': 2, 'card': 'scene2', 'story_order': 2})
                    else:
                        candidate['members'].extend([
                            {'key': 'ch2', 'kind': 'chapter', 'body': {'title': '确认旧印', 'goal': '查证', 'consequence': '得到线索'}},
                            {'key': 'vol', 'kind': 'volume', 'body': {'title': '查井', 'goal': '求证', 'turn': '获得线索'}}])
                        candidate['chapters'].append({'index': 2, 'card': 'ch2', 'scenes': [
                            {'index': 1, 'card': 'scene2', 'story_order': 2}]})
                    scope = {'kind': self.kind, 'chapters': [1] if self.kind == 'chapter' else [1, 2]}
                    if self.kind == 'book':
                        scope['expected_chapters'] = 2
                    candidate['material_bindings'] = {
                        'scene': {ident: {'disposition': 'deferred', 'reason': '整章完成后统一核验'}},
                        'scene2': {ident: {
                            'function': '核验整章两场的因果', 'parameter': '进入调查与取得证据',
                            'observable': '两场行动推进到辨认旧印', 'check': '两个目标对应章末后果',
                            'review_scope': scope,
                            'source_scope': {field['id']: {'disposition': 'required', 'reason': '整章核查该原判据'}
                                             for field in fields}}}}
                    if self.third_scene_chars is not None:
                        bindings = candidate['material_bindings']
                        bindings['scene3'] = bindings['scene2']
                        for index in (3, 4):
                            extra = deepcopy(other)
                            extra['key'] = f'scene{index}'
                            extra['body']['title'] = f'旧印查证第{index}场'
                            candidate['members'].append(extra)
                            candidate['chapters'][0]['scenes'].append({
                                'index': index, 'card': extra['key'], 'story_order': index})
                        for key in ('scene2', 'scene4'):
                            bindings[key] = {ident: {'disposition': 'deferred', 'reason': '指定第三场核验前三场的篇幅'}}
            output.text = json.dumps(raw, ensure_ascii=False)
            return output
        if '{"operations"' in prompt:
            self.calls.append(messages)
            return GenResult('{"operations":[]}', 'complete', {}, 'fake', {})
        if '只输出正文' in prompt:
            self.calls.append(messages)
            assert all('scope_review' not in item['text'] for item in data['items'])
            if self.third_scene_chars is not None:
                count = (15, 20, self.third_scene_chars)[self.written]
                self.written += 1
                return GenResult('[FAKE] ' + '沈' * (count - 6), 'complete', {}, 'fake', {})
            return GenResult('[FAKE] 沈砚举灯查看井壁的旧印，封条的痕迹在光下显出。他记下证据继续调查。',
                             'complete', {}, 'fake', {})
        return super().generate(messages, **params)


def designed_story(tmp_path, pin, provider):
    store = Store(tmp_path / 'test_scope', create=True, test_mode=True)
    store.init_project('隔离范围审稿')
    store.add_brief('两场完成暗井调查')
    adopt_story(store, baseline(), {})
    detail = 'chapter' if provider.kind == 'chapter' else 'volume'
    job = start_job(store, JobRequest('design', budget=Budget(32, 90000, 4000), materials=[pin], design_scope=detail)).id
    assert resume_job(store, job, provider, config(store)).step == 'plan:book:confirm'
    assert resume_job(store, job, provider, config(store), choose).step == f'plan:{detail}:confirm'
    result = resume_job(store, job, provider, config(store), choose)
    assert result.status == 'DONE', result.reason
    scenes = [row['scene_id'] for chapter in result.outputs['application']['chapters'] for row in chapter['scenes']]
    return store, scenes


@pytest.mark.parametrize('failure', ['', 'omit', 'old_hash', 'failed'])
def test_scope_review_gates_normal_batch_acceptance(tmp_path, monkeypatch, failure):
    pin = source_pin(tmp_path, monkeypatch)
    provider = ScopeModel(failure)
    store, scenes = designed_story(tmp_path, pin, provider)
    with store:
        job = start_job(store, JobRequest('write', scene_ids=scenes, budget=Budget(16, 90000, 4000, 0))).id
        result = resume_job(store, job, provider, config(store), author())
        if failure:
            assert result.status == 'BLOCKED', result
            assert not store.list('accepted')
        else:
            assert result.status == 'DONE', result.reason
            assert len(store.list('accepted')) == 2
            assert any('material_scope_review' in call[-1]['content'] for call in provider.calls)
            calls = len(provider.calls)
            assert resume_job(store, job, provider, config(store)).status == 'DONE'
            assert len(provider.calls) == calls


def test_selected_chapter_ending_check_reaches_a_complete_chapter_review(tmp_path, monkeypatch):
    from nw.materials.work_catalog import SourceDesk

    key = '板块96 结尾规则检查#全章结尾'
    text = ('## 板块96 结尾规则检查\n\n### 全章结尾\n\n'
            '【定义】全章结尾是否以新威胁出现或旧威胁升级结束。\n'
            '【指令】全章结尾是否以新威胁出现或旧威胁升级结束。\n'
            '【判定标准】章节最后一句话是否制造了“接下来会发生什么”的冲动。\n')
    source_root = tmp_path / 'sources'
    content = text.encode()
    monkeypatch.setitem(library_adjudication._PINNED, 'library', sha256(content).hexdigest())
    build_catalog(tmp_path, source_root, _manifest(source_root, tmp_path, [('library.txt', 'library', content)]))
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)
    item = next(row for row in SourceDesk(tmp_path).rows if row['key'] == key)
    assert item['profile'] == 'scope_review'
    pin = {name: item[name] for name in ('id','file_sha256','sha256')}
    pin.update(disposition='required', reason='检查整章章末留下的实际问题')

    provider = ScopeModel()
    store, scenes = designed_story(tmp_path, pin, provider)
    with store:
        job = start_job(store, JobRequest('write', scene_ids=scenes, budget=Budget(16, 90000, 4000, 0))).id
        assert resume_job(store, job, provider, config(store), author()).status == 'DONE'
        review, = [call for call in provider.calls if 'material_scope_review' in json.loads(call[-1]['content'])]
        assert review[0]['content'].splitlines().count(f'### {key}') == 1
        assert '引用完整章稿的末句和实际变化' in review[0]['content']
        contract = json.loads(review[-1]['content'])['material_scope_review']
        assert [draft['scene_index'] for draft in contract['drafts']] == [1,2]
        assert all(draft['ref']['sha256'] for draft in contract['drafts'])
        assert contract['checks'][0]['source_contract']['key'] == key
        assert len(store.list('accepted')) == 2


def test_selected_sensory_scope_rule_sends_its_writing_guidance_to_the_bound_scene(tmp_path, monkeypatch):
    from nw.materials.work_catalog import SourceDesk

    key = '板块52 感官描写#五感规则'
    content = ('## 板块52 感官描写\n\n### 五感规则\n\n'
               '【定义】每章至少使用3种感官描写。\n'
               '【指令】每章至少包含视觉、听觉和触觉三种基础感官。\n'
               '【判定标准】逐处核对本章的可感段落。\n').encode()
    root = tmp_path / 'sources'
    monkeypatch.setitem(library_adjudication._PINNED, 'library', sha256(content).hexdigest())
    build_catalog(tmp_path, root, _manifest(root, tmp_path, [('library.txt', 'library', content)]))
    index_units(tmp_path, None)
    build_adjudications(tmp_path)
    from fake_binding_reviews import install_review_fixtures
    install_review_fixtures(tmp_path)
    item = next(row for row in SourceDesk(tmp_path).rows if row['key'] == key)
    assert item['profile'] == 'scope_review'
    pin = {name: item[name] for name in ('id', 'file_sha256', 'sha256')}
    pin.update(disposition='required', reason='检查本章感官描写')

    provider = ScopeModel()
    store, scenes = designed_story(tmp_path, pin, provider)
    with store:
        job = start_job(store, JobRequest('write', scene_ids=scenes, budget=Budget(16, 90000, 4000, 0))).id
        written = resume_job(store, job, provider, config(store), author())
        assert written.status == 'DONE', written.reason
        first, bound = [call for call in provider.calls if call[0]['content'].startswith('按作者约束和本场任务写正文')]
        for call in (first, bound):
            assert call[0]['content'].splitlines().count(f'### {key}') == 1
            assert '视、听、触安排到相应稿段' in call[0]['content']
            assert 'material_scope_review' not in json.loads(call[-1]['content'])
        assert len(store.list('accepted')) == 2


def test_a_single_scene_cannot_prove_a_whole_chapter(tmp_path, monkeypatch):
    pin = source_pin(tmp_path, monkeypatch)
    provider = ScopeModel()
    store, scenes = designed_story(tmp_path, pin, provider)
    with store:
        job = start_job(store, JobRequest('write', scene_ids=[scenes[1]], budget=Budget(10, 90000, 4000, 0))).id
        result = resume_job(store, job, provider, config(store), author())
        assert result.status == 'BLOCKED' and 'MATERIAL_SCOPE_INCOMPLETE' in result.reason
        assert not store.list('accepted')
        assert not any('只输出正文' in call[0]['content'] for call in provider.calls)


@pytest.mark.parametrize('kind,failure', [('cross_chapter', ''), ('cross_chapter', 'one_chapter'), ('book', '')])
def test_cross_chapter_and_full_book_need_all_declared_chapters(tmp_path, monkeypatch, kind, failure):
    pin = source_pin(tmp_path, monkeypatch, kind)
    provider = ScopeModel(failure, kind)
    store, scenes = designed_story(tmp_path, pin, provider)
    with store:
        job = start_job(store, JobRequest('write', scene_ids=scenes, budget=Budget(16, 90000, 4000, 0))).id
        result = resume_job(store, job, provider, config(store), author())
        assert result.status == ('BLOCKED' if failure else 'DONE'), result.reason
        assert len(store.list('accepted')) == (0 if failure else 2)


def test_acceptance_revalidates_scope_review_instead_of_trusting_cached_pass(tmp_path, monkeypatch):
    pin = source_pin(tmp_path, monkeypatch)
    provider = ScopeModel()
    store, scenes = designed_story(tmp_path, pin, provider)
    with store:
        job = start_job(store, JobRequest('write', scene_ids=scenes, budget=Budget(16, 90000, 4000, 0))).id
        def tamper(step, payload):
            assert step == 'batch:confirm'
            run_id = payload['material_scope_review']['run_id']
            row = store.get('run', run_id)
            changed = json.loads(row.output_text)
            changed['material_checks'][0]['source_checks'][0]['status'] = 'failed'
            with store.connection:
                store.connection.execute('UPDATE runs SET output_text=? WHERE id=?', (json.dumps(changed), run_id))
            return {'action': 'accept', 'reason': '核对范围'}
        result = resume_job(store, job, provider, config(store), tamper)
        assert result.status == 'BLOCKED' and 'every required scope check' in result.reason
        assert not store.list('accepted')


@pytest.mark.parametrize('third_scene_chars,status', [(24, 'BLOCKED'), (25, 'DONE')])
def test_scene_length_reviews_only_three_required_drafts(tmp_path, monkeypatch, third_scene_chars, status):
    pin = source_pin(tmp_path, monkeypatch, scene_length=True)
    provider = ScopeModel(third_scene_chars=third_scene_chars)
    store, scenes = designed_story(tmp_path, pin, provider)
    with store:
        assert len(scenes) == 4
        job = start_job(store, JobRequest('write', scene_ids=scenes[:3], budget=Budget(18, 90000, 4000, 0))).id
        result = resume_job(store, job, provider, config(store), author())
        assert result.status == status, result.reason
        assert len(store.list('accepted')) == (3 if status == 'DONE' else 0)
        if status == 'BLOCKED':
            assert 'MATERIAL_SCOPE_REVIEW' in result.reason


@pytest.mark.parametrize('title,bad,good', [
    ('连续节奏检查', [[1, 3], [1, 2, 4], [1, 2, 3, 4]], [2, 3, 4]),
    ('重章间隔', [[1, 3, 4]], [1, 2, 3, 4]),
    ('情绪承接', [[1, 4], [2, 3, 4]], [3, 4]),
])
def test_source_scope_window_must_match_required_contiguous_chapters(title, bad, good):
    from nw.materials.binding import _validate_review_scope

    scope, = [scope for (key, _), scope in library_adjudication._SCOPED_LIBRARY_CHECKS.items()
              if key.endswith('#' + title)]
    row = {'review': {'contract': {'evidence_scope': scope}}}
    candidate = {'chapters': [{'index': 4, 'scenes': [{'card': 's'}]}]}
    for chapters in bad:
        with pytest.raises(ValueError, match='MATERIAL_DESIGN'):
            _validate_review_scope({'kind': 'cross_chapter', 'chapters': chapters}, row, candidate, 's')
    _validate_review_scope({'kind': 'cross_chapter', 'chapters': good}, row, candidate, 's')


def test_chapter_emotion_uses_previous_last_and_next_first_sentence():
    from nw.materials.scoped import _covers_scope

    check = {'binding': {'review_scope': {'chapters': [3, 4]}},
             'source_contract': {'evidence_scope': {'chapter_boundary_sentences': True}}}
    text = '  她终于把手收回袖中。闭上眼睛却不见天光。 \n'
    visible = {ident: {'ref': {'id': ident}, 'chapter_index': chapter, 'scene_index': index, 'text': text}
               for ident, chapter, index in [('a', 3, 1), ('b', 3, 2), ('c', 4, 1), ('d', 4, 2)]}
    early = {'id': 'c', 'start': 2, 'end': 12, 'quote': text[2:12]}
    late = {'id': 'b', 'start': 12, 'end': len(text.rstrip()), 'quote': text[12:].rstrip()}
    assert _covers_scope([late, early], visible, check)
    assert not _covers_scope([{**late, 'id': 'a'}, early], visible, check)
    assert not _covers_scope([late, {**early, 'start': 3}], visible, check)
