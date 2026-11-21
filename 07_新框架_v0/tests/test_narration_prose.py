from dataclasses import asdict
import json

import pytest

from nw.cards import decide_card
from nw.context.story import StoryScope, build_story_context
from nw.materials.action_review import review_result
from nw.materials.narration_review import FIXES, check_state_audience
from nw.materials.steps.review import MATERIAL as REVIEW_MATERIAL
from nw.materials.steps.writing import MATERIAL as WRITING_MATERIAL
from nw.scene_messages import draft_messages
from nw.store import Store
from nw.story_state import adopt_story
from story_fixture import baseline, seed_book
from test_material_action_review import draft, review_run, span
from test_selection import add_card


def test_switching_pov_switches_interiority_but_preserves_visible_speech(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        scenes = seed_book(store, 2)
        approved = []
        for ident in ('lin', 'mo'):
            character = {'name': ident, 'role': '同事', 'visibility': 'public',
                         'want': f'私下目的-{ident}', 'wound': f'私人旧事-{ident}', 'voice': f'口头习惯-{ident}'}
            scene = {'title': '核对公函', 'goal': '确认交接', 'pov': ident, 'characters': ['lin', 'mo'],
                     'character_goals': {key: f'本场隐情-{key}' for key in ('lin', 'mo')}}
            for key, kind, body in ((ident, 'character', character), ('scene-' + ident, 'scene', scene)):
                ref = add_card(store, key, kind, body)
                approval = decide_card(store, ref, 'approved', '测试')
                approved.append({**asdict(ref), 'decision_id': approval.id})
        facts = [{'entity_id': 'letter', 'predicate': 'sender', 'holder': key, 'claim': 'belief',
                  'value': f'我的猜测-{key}', 'story_order': 0, 'disclosure_order': [0, 0, 0]}
                 for key in ('lin', 'mo')]
        adopt_story(store, baseline(card_refs=approved, facts=facts), {})
        for index, (pov, other) in enumerate((('lin', 'mo'), ('mo', 'lin'))):
            scope = StoryScope('main', 0, index + 1, {'card_id': 'scene-' + pov, 'version': 1})
            work = build_story_context(store, scenes[index].id, scope, 20000)
            visible = json.dumps(work.package, ensure_ascii=False)
            assert f'口头习惯-{other}' in visible
            for category in ('我的猜测', '私人旧事', '私下目的', '本场隐情'):
                assert f'{category}-{pov}' in visible and f'{category}-{other}' not in visible
            assert '前史可以只改变' in work.prompt


def beat(order):
    return {'id': f'work:narration:s:{order}', 'profile': 'method_work', 'narration_order': order}


def judgment(check, spans, status='pass', issue='as_designed'):
    label = '' if issue == 'as_designed' else f'[{issue}] '
    return {'id': check['id'], 'status': status, 'reason': label + '独立审稿判断。REVIEWER_PRIVATE_NOTE',
            'evidence': spans}


def test_narration_review_repairs_known_defects_with_safe_current_draft_locations(draft):
    first, second = beat(1), beat(2)
    contract = {'checks': [second, first]}
    cut = draft.text.index('。') + 1
    a, b = span(draft, 0, cut), span(draft, cut, len(draft.text))
    review_prompt, _ = draft_messages({}, 'review', draft, None, contract, REVIEW_MATERIAL, ())
    assert 'work:narration:' in review_prompt[0]['content'] and '[viewpoint]' in review_prompt[0]['content']
    rows = [judgment(second, [a]), judgment(first, [b])]
    result = review_result(review_run(draft, rows), contract, draft, None)
    assert result['recommendation'] == 'revise'
    assert result['material_checks'][0]['narration_issue'] == 'order'

    def reviser_input(rows):
        result = review_result(review_run(draft, rows), contract, draft, None)
        assert result['recommendation'] == 'revise'
        messages, _ = draft_messages({}, 'revise', draft, result, None, WRITING_MATERIAL, ())
        assert 'REVIEWER_PRIVATE_NOTE' not in messages[-1]['content']
        return json.loads(messages[-1]['content'])['review']['material_checks'][0]

    wrong_pov = reviser_input([judgment(second, [b], issue='viewpoint'), judgment(first, [a])])
    assert (wrong_pov['status'], wrong_pov['fix']) == ('failed', FIXES['viewpoint'])
    assert wrong_pov['draft_locations'] == [{'start': cut, 'end': len(draft.text)}]
    missing = reviser_input([judgment(second, [], 'failed', 'missing'), judgment(first, [a])])
    assert missing['fix'] == FIXES['missing'] and missing['draft_locations'] == []
    good = [judgment(second, [a]), judgment(first, [a])]
    assert review_result(review_run(draft, good), contract, draft, None)['recommendation'] == 'pass'
    wrong_span = {**b, 'quote': '无此原句'}
    with pytest.raises(ValueError, match='MATERIAL_EVIDENCE'):
        review_result(review_run(draft, [judgment(second, [wrong_span]), judgment(first, [a])]), contract, draft, None)


def test_acceptance_rechecks_durable_four_field_review_for_narration(draft, monkeypatch):
    from types import SimpleNamespace
    from nw.materials import action_review, evidence

    check = {**beat(1), 'method_artifact': {'narration': {'owner': None, 'time': 'past'}}}
    contract = {'checks': [check]}
    cut = draft.text.index('。') + 1
    row = judgment(check, [span(draft, 0, cut)], issue='viewpoint')
    native = evidence.review_result(review_run(draft, [row]), contract, draft, None)
    assert native['recommendation'] == 'pass'
    assert set(native['material_checks'][0]) == {'id', 'status', 'reason', 'evidence'}
    monkeypatch.setattr(evidence, 'check_material_acceptance', lambda *_: [row.copy()])
    monkeypatch.setattr(action_review, 'read_input_manifest', lambda *_: ({}, {'material_review_run': 'r'}))
    message = json.dumps({'material_review': contract})
    run = SimpleNamespace(input_snapshot_json=json.dumps({'messages': [{'content': message}]}))
    store = SimpleNamespace(get=lambda *_: run)
    delta = SimpleNamespace(manifest_id='m', operations=[{'holder': 'yan', 'evidence': row['evidence']}])
    with pytest.raises(ValueError, match='approved narration'):
        action_review.check_material_acceptance(store, draft, delta)
    row['reason'] = '这段前史提前向读者揭示了封存单的来历'
    with pytest.raises(ValueError, match='仅向读者讲述'):
        action_review.check_material_acceptance(store, draft, delta)


def test_approved_narration_reaches_write_review_revision_and_reopened_draft(tmp_path):
    from dataclasses import replace

    from nw.novel_flow import JobRequest, resume_job, start_job
    from nw.context.prior_prose import prior_prose
    from nw.story_state import current_head, revision_state
    from nw.task_models import Budget
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_material_stage_roundtrip import StageModel
    from test_material_workflow import choose
    from test_novel_flow import author, config

    reader_secret = '五年前，这份库契已经在另一座城被悄悄抵押。'
    visible_action = '沈砚用灯照过纸角，铜丝在他手背划出一道口子。'

    class Reader(PhaseModel, StageModel):
        reviewed = 0

        def generate(self, messages, **params):
            data = json.loads(messages[-1]['content'])
            result = super().generate(messages, **params)
            if data.get('stage') == 'expression_design':
                raw = json.loads(result.text)
                guide = raw['products']['guidance'][0]
                bases = data['narration_bases'][guide['scene']]
                ref = next(k for k, b in bases.items() if b['text'] == reader_secret)
                raw['products']['guidance'].insert(0, {'scene': guide['scene'], 'observable': reader_secret,
                    'check': '只有读者提前得知库契已被抵押', 'narration': {'time': 'past', 'mode': 'summary',
                    'owner': None, 'basis_ref': ref, 'basis_quote': reader_secret, 'effect': '读者明白查验一事的代价'}})
                result.text = json.dumps(raw, ensure_ascii=False)
            elif 'material_review' in data:
                self.reviewed += 1
                checks = [c for c in data['material_review']['checks'] if 'narration_order' in c]
                raw = json.loads(result.text)
                secret_id = next(c['id'] for c in checks if c['method_artifact']['narration']['owner'] is None)
                text = data['draft']['text']
                cut = text.index('\n')
                for row in raw['material_checks']:
                    start, end = (0, cut) if row['id'] == secret_id else (cut + 1, len(text))
                    row['evidence'] = [{**data['material_review']['draft'], 'start': start, 'end': end,
                                        'quote': text[start:end]}]
                if self.reviewed == 1:
                    row = next(r for r in raw['material_checks'] if r['id'] == checks[0]['id'])
                    row.update(status='unverified', reason='[expression] PRIVATE_REVIEW_JUDGMENT')
                result.text = json.dumps(raw, ensure_ascii=False)
            elif data.get('review'):
                feedback = next(r for r in data['review']['material_checks'] if 'fix' in r)
                assert feedback['fix'] == FIXES['expression'] and feedback['draft_locations']
                assert 'PRIVATE_REVIEW_JUDGMENT' not in messages[-1]['content']
                assert any(i['source'] == 'material:' + feedback['id'] for i in data['context']['items'])
                result.text = '[FAKE] ' + reader_secret + '\n' + visible_action + '他又把纸角轻轻托住。'
            elif 'items' in data:
                result.text = '[FAKE] ' + reader_secret + '\n' + visible_action
            elif '{"operations"' in messages[0]['content']:
                raw = json.loads(result.text)
                audience = data['context']['reader_only_spans']
                private = [span for span in audience if 'holders' not in span]
                assert private == [{'start': 0, 'end': data['draft']['text'].index('\n'), 'time': 'past'}]
                assert any(span.get('mode') == 'action' and span['holders'] for span in audience)
                with pytest.raises(ValueError, match='仅向读者讲述'):
                    check_state_audience([{'holder': 'yan', 'evidence': private}], audience)
                with pytest.raises(ValueError, match='世界变化'):
                    check_state_audience([{'holder': 'WORLD', 'evidence': private}], audience)
                check_state_audience([{'holder': 'READER', 'evidence': audience}], audience)
                for operation in raw['operations']:
                    operation.setdefault('expected_old', None)
                    operation['evidence'][0]['start'] = data['draft']['text'].index('\n') + 1
                result.text = json.dumps(raw, ensure_ascii=False)
            return result

    template_catalog(tmp_path)
    folder = tmp_path / 'novel'
    with Store(folder, create=True, test_mode=True) as store:
        store.init_project('[FAKE] 叙述计划贯通')
        store.add_brief('核对封条后决定如何处置')
        adopt_story(store, baseline(facts=[{'holder': 'READER', 'claim': 'fact', 'entity_id': 'deed',
            'predicate': 'history', 'value': reader_secret, 'story_order': 0, 'disclosure_order': [0, 0, 0]}]), {})
        model = Reader('fixture')
        runtime = replace(config(store), source_driven=True)
        design = start_job(store, JobRequest('design', budget=Budget(40, 120000, 4000))).id
        assert resume_job(store, design, model, runtime).step == 'plan:book:confirm'
        assert resume_job(store, design, model, runtime, choose).step == 'plan:chapter:confirm'
        planned = resume_job(store, design, model, runtime, choose)
        assert planned.status == 'DONE', planned.reason
        scene, = store.list('scene')
        job = start_job(store, JobRequest('write', scene_ids=[scene.id], budget=Budget(16, 120000, 4000, 1))).id
        written = resume_job(store, job, model, runtime, author())
        assert written.status == 'DONE', written.reason
        assert model.reviewed == 2 and len(store.drafts(scene.id)) == 2
    with Store(folder, test_mode=True) as reopened:
        selected = reopened.accepted(scene.id)
        draft = reopened.get('draft', selected.draft_id)
        assert draft.text.endswith('把纸角轻轻托住。')
        slot = revision_state(reopened, current_head(reopened))['slots'][scene.id]
        scope = json.loads(scene.card_json)['story']['scene_ref']
        from nw.cards import read_card
        from nw.story_models import CardRef
        pov = read_card(reopened, CardRef(**scope))['body']['pov']
        text, hidden = prior_prose(reopened, draft, slot, pov)
        assert hidden == [(0, text.index('\n') + 1)]
        assert visible_action in text[hidden[0][1]:] and reader_secret not in text[hidden[0][1]:]
        assert prior_prose(reopened, draft, {'delta_id': None}, pov)[1] == [(0, len(text))]
        assert prior_prose(reopened, draft, slot, 'other')[1] == [(0, len(text))]
