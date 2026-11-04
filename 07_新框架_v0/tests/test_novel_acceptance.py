
"""Engineering acceptance with isolated projects and simulated model responses."""
from dataclasses import asdict
import json
from pathlib import Path

import pytest

from nw.cards import decide_card, save_card
from nw.llm.base import GenResult
from nw.novel_flow import resume_job, show_job
from nw.novel_store import Journal
from nw.store import Store
from nw.story_state import adopt_story, current_head, state_at
from nw.task_models import content_sha256
from story_fixture import baseline
from test_cli import invoke
from test_migration_v5 import v4_fixture
from test_novel_flow import Model, author, config, job, setup_story
from test_providers import server


def _card(store, ident, kind, body):
    card = save_card(store, {'card_id': ident, 'kind': kind, 'origin': 'author', 'body': body}, None)
    approved = decide_card(store, card, 'approved', '隔离验收')
    return {**asdict(card), 'decision_id': approved.id}


def _scene(store, chapter, index, time):
    ref = _card(store, f'scene-{chapter.index}-{index}', 'scene', {
        'title': '封条', 'goal': '调查封条', 'pov': 'yan', 'story_time': str(time)})
    scene = store.add_scene(chapter.id, index, json.dumps({'story': {
        'story_order': time, 'scene_ref': {key: ref[key] for key in ('card_id', 'version')}}}))
    return scene.id, ref


def _character(store):
    return _card(store, 'yan', 'character', {
        'name': '沈砚', 'role': '主角', 'want': '查清封条', 'visibility': 'public'})


def test_full_upgrade_then_continue_and_export(tmp_path, server):
    endpoint, state = server
    project = tmp_path / 'book'
    project.mkdir()
    v4_fixture(project)
    settings = tmp_path / 'model.toml'
    settings.write_text(f'[model]\nprovider="ollama"\nbase_url="{endpoint}"\nmodel="test"\n', encoding='utf-8')

    def cli(*args):
        proc = invoke(tmp_path, '--project', 'book', '--config', str(settings), *args)
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    assert cli('show', 'accepted')[0]['draft_id'] == 'd2'
    assert (project / '正文' / 'ch01_s01.md').read_text(encoding='utf-8') == '二稿'
    for target in ({'scene_id': 's'}, {'run_id': 'r4'}):
        path = tmp_path / 'decision.json'
        path.write_text(json.dumps({'action': 'abandon', 'targets': target, 'reason': '历史任务封存'}),
                        encoding='utf-8')
        cli('story', 'decide', '--file', str(path))
    with Store(project) as store:
        scene, scene_card = _scene(store, store.add_chapter(2, '下一章'), 1, 2)
        base = baseline(as_of_story_order=1, disclosure_order=[1, 1, 0],
                        card_refs=[_character(store), scene_card])
    adoption = tmp_path / 'adopt.json'
    adoption.write_text(json.dumps({'baseline': base, 'baseline_sha256': content_sha256(base),
                                   'expected_accepted': {'s': 'd2'}}), encoding='utf-8')
    cli('story', 'adopt', '--baseline', str(adoption))
    request = tmp_path / 'job.json'
    request.write_text(json.dumps({'mode': 'continue', 'budget': {
        'max_calls': 4, 'context_char_limit': 45000, 'output_limit': 2000}}), encoding='utf-8')
    ident = cli('novel', 'start', '--request', str(request))['id']
    model = Model()

    def respond(body):
        result = model.generate(body['messages'])
        return {'done': True, 'done_reason': 'stop', 'message': {'content': result.text}}

    state['respond'] = respond
    waiting = cli('novel', 'resume', '--job', ident)
    assert waiting['outputs']['scope']['scene_ids'] == [scene]
    decision = tmp_path / 'accept.json'
    decision.write_text(json.dumps({'step': waiting['step'], 'token': waiting['outputs']['gate']['token'],
                                    'action': 'accept', 'reason': '工程验收'}), encoding='utf-8')
    assert cli('novel', 'resume', '--job', ident, '--decision', str(decision))['status'] == 'DONE'
    with Store(project) as store:
        assert store.accepted('s').draft_id == 'd2'
        assert store.run_output('r1')['raw'] == {'original': '初稿'}
        assert store.accepted(scene)
        assert store.connection.execute('PRAGMA user_version').fetchone()[0] == 8
        assert store.connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert store.connection.execute('PRAGMA foreign_key_check').fetchall() == []
    assert len(list(project.glob('nw.v*.bak'))) == 4
    assert (project / '正文' / 'ch02_s01.md').read_text(encoding='utf-8').startswith('[FAKE]')


def _operation(payload, *, op='set', entity, predicate, holder, old=None, value, claim='fact'):
    return {'op': op, 'entity_id': entity, 'predicate': predicate, 'holder': holder, 'claim': claim,
            'story_order': payload['story_order'], 'disclosure_order': payload['disclosure_order'],
            'expected_old': old, 'new_value': value, 'evidence': [payload['evidence_format']]}


def test_three_scenes_track_item_knowledge_and_promise(tmp_path):
    class Continuity(Model):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            prompt, data = messages[0]['content'], json.loads(messages[-1]['content'])
            if 'items' in data:
                scene = next(item['source'] for item in data['items'] if item['source'].startswith('scene:'))
                prose = {
                    'scene:scene-1-1': '沈砚拿起钥匙，摸到七道刻痕。七道刻痕到底记录了什么？',
                    'scene:scene-1-2': '沈砚把钥匙交给陆昭，请她带去复验。',
                    'scene:scene-2-1': '沈砚核对簿册，发现那七道刻痕正好对应七次查验。',
                }[scene]
                result.text = '[FAKE] ' + prose
                return result
            if '{"operations"' not in prompt:
                return result
            match data['disclosure_order'][:2]:
                case [1, 1]:
                    operations = [
                        _operation(data, entity='key', predicate='owner', holder='WORLD', value='yan'),
                        _operation(data, entity='well', predicate='key_mark', holder='yan', value='七道刻痕'),
                        _operation(data, op='introduce_promise', entity='well', predicate='echo',
                                   holder='READER', value='七道刻痕待查'),
                    ]
                case [1, 2]:
                    operations = [_operation(data, entity='key', predicate='owner', holder='WORLD',
                                             old='yan', value='lu')]
                case _:
                    operations = [_operation(data, op='advance_promise', entity='well', predicate='echo',
                                             holder='READER', old='七道刻痕待查', value='刻痕对应七次查验')]
            result.text = json.dumps({'operations': operations}, ensure_ascii=False)
            return result

    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('跨章验收')
        store.add_brief('追查井口钥匙上的七道刻痕')
        first = store.add_chapter(1, '封条')
        second = store.add_chapter(2, '查验')
        pairs = [_scene(store, first, 1, 1), _scene(store, first, 2, 2), _scene(store, second, 1, 3)]
        adopt_story(store, baseline(card_refs=[_character(store), *(card for _, card in pairs)]), {})
        provider = Continuity()
        ident = job(store, [scene for scene, _ in pairs], calls=12)
        pending = resume_job(store, ident, provider, config(store))
        assert pending.step == 'batch:confirm', pending.reason
        assert '七道刻痕' in provider.calls[8][-1]['content']
        assert current_head(store).revision == 0 and not store.list('accepted')
        assert resume_job(store, ident, provider, config(store), author()).status == 'DONE'

    with Store(tmp_path, test_mode=True) as store:
        head = current_head(store)
        assert [fact.value for fact in state_at(store, 'main', head.revision, 1, 'WORLD').facts] == ['yan']
        assert [fact.value for fact in state_at(store, 'main', head.revision, 3, 'WORLD').facts] == ['lu']
        assert [fact.value for fact in state_at(store, 'main', head.revision, 3, 'yan').facts] == ['七道刻痕']
        assert [fact.value for fact in state_at(store, 'main', head.revision, 3, 'READER', (1, 2, 0)).facts] == [
            '七道刻痕待查']
        assert [fact.value for fact in state_at(store, 'main', head.revision, 1, 'READER', (2, 1, 0)).facts] == [
            '刻痕对应七次查验']
        assert len(store.list('accepted')) == 3


CASES = json.loads((Path(__file__).resolve().parents[1] / 'fixtures/story_seed/failure_cases.json').read_text(
    encoding='utf-8'))


@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
@pytest.mark.parametrize('classification', ['typed', 'laundered', 'holder'])
def test_false_speech_and_future_plan_never_become_fact(tmp_path, case, classification):
    class EvidenceModel(Model):
        def generate(self, messages, **params):
            prompt, data = messages[0]['content'], json.loads(messages[-1]['content'])
            if '{"operations"' in prompt:
                holder = 'yan' if classification == 'holder' else 'WORLD'
                claim = 'fact' if classification == 'laundered' else case['claim']
                result = {'operations': [_operation(data, entity='well', predicate=case['id'],
                               holder=holder, value=case['value'], claim=claim)]}
            elif '{"findings"' in prompt and classification == 'laundered':
                result = {'findings': [{
                    'code': case['finding'], 'severity': 'hard', 'status': 'OPEN', 'target_ref': data['target_ref'],
                    'evidence': [data['evidence_format']], 'explanation': '证据只支持说辞或打算',
                    'suggested_action': '保留为人物的说辞或计划'}]}
            elif '{"recommendation"' in prompt or '{"findings"' in prompt:
                return super().generate(messages, **params)
            else:
                return GenResult('[FAKE] ' + case['text'], 'complete', {}, 'test', {})
            return GenResult(json.dumps(result, ensure_ascii=False), 'complete', {}, 'test', {})

    with Store(tmp_path, create=True, test_mode=True) as store:
        ident = job(store, setup_story(store, 1))
        provider = EvidenceModel()
        result = resume_job(store, ident, provider, config(store))
        if classification == 'holder':
            assert result.step == 'batch:confirm'
            assert resume_job(store, ident, provider, config(store), author()).status == 'DONE'
            assert [f.claim for f in state_at(store, 'main', 1, 1, 'yan').facts] == [case['claim']]
        else:
            assert result.status == 'BLOCKED' and not store.list('accepted')
            expected = 'HARD_FACT_FINDINGS' if classification == 'laundered' else 'INVALID'
            assert expected in result.reason
        assert not state_at(store, 'main', current_head(store).revision, 1, 'WORLD').facts


@pytest.mark.parametrize('stage', ['write', 'delta:extract', 'delta:fact-review', 'delta'])
def test_recovery_at_every_commit_boundary(tmp_path, monkeypatch, stage):
    original = Journal.result
    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = setup_story(store, 1)
        ident = job(store, [scene], calls=4)
        provider = Model()

        def stop_after_durable_output(self, key, status, output):
            if key == f'scene:{scene}:{stage}' and status == 'DONE':
                raise KeyboardInterrupt
            return original(self, key, status, output)

        with monkeypatch.context() as interrupted:
            interrupted.setattr(Journal, 'result', stop_after_durable_output)
            with pytest.raises(KeyboardInterrupt):
                resume_job(store, ident, provider, config(store))
        assert current_head(store).revision == 0
    with Store(tmp_path, test_mode=True) as store:
        assert resume_job(store, ident, provider, config(store)).step == 'batch:confirm'
        assert resume_job(store, ident, provider, config(store), author()).status == 'DONE'
        assert len(provider.calls) == 4
        assert show_job(store, ident).outputs['budget']['used_calls'] == 4
        assert len(store.list('accepted')) == 1
