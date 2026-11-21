from dataclasses import replace
import json

import pytest

from nw.materials import action_review, narration_review
from nw.materials.evidence import writer_checks
from nw.materials.passage_review import FIXES
from nw.materials.template_support import events
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.store import Store
from nw.story_state import adopt_story
from nw.task_models import Budget
from story_fixture import baseline
from test_material_action_review import draft, review_run, span
from test_material_phase_flow import PhaseModel, template_catalog
from test_material_stage_roundtrip import StageModel
from test_material_workflow import choose
from test_novel_flow import author, config


EXAMPLES = {
    'procedure_branch': [
        ('demonstration', '先到的人签了借条，当场拿到一盏灯。', 'scene'),
        ('compression', '前头三人照办，窗外的影子短了一截。', 'ellipsis'),
        ('different_choice', '轮到沈砚，他把借条推回去，指了指窗下的日光。', 'scene'),
        ('handoff', '他翻开领件凭单，上面写着午后才能来取封条。', 'scene')],
    'focus_relay': [
        ('orientation', '档案室的窗子开着，一排人正低头抄录卷号。', 'summary'),
        ('attention', '木架那头轻轻响了一声，几支笔一起停住。', 'scene'),
        ('focus', '沈砚手背上挑着根铜丝，封条的纸角已经翘开。', 'pause')],
}
WRONG_ENDING = {
    'procedure_branch': '凭单一翻过来，封条就已经取回来了。',
    'focus_relay': '沈砚的眼睛刚扫过去，就知道对方心里认定旧印是假的。',
}


class PassageModel(PhaseModel, StageModel):
    def __init__(self, kind):
        super().__init__('fixture')
        self.kind = kind
        self.reviews = 0
        self.revisions = 0

    def generate(self, messages, **params):
        data = json.loads(messages[-1]['content'])
        result = super().generate(messages, **params)
        example = EXAMPLES[self.kind]
        if data.get('stage') == 'scene_design':
            raw = json.loads(result.text)
            scene, = raw['products']['selected_events']
            event = events(data['inputs'])[scene['event']]
            raw['products']['passage_choices'] = [{**scene, 'kind': self.kind, 'source_ref': None,
                'need_quote': event.get('goal') or event['event'], 'reason': '审稿独见设计理由，借办理或注意力变化展开查验。'}]
            result.text = json.dumps(raw, ensure_ascii=False)
        elif data.get('stage') == 'expression_design':
            raw = json.loads(result.text)
            guides = raw['products']['guidance']
            base = guides[-1]
            steps = []
            for i, (role, sentence, detail) in enumerate(example):
                # Existing scene/first-appearance obligations stay ahead of the selected series.
                beat = {**base['narration'], 'effect': '借现场线索交代下一步'}
                if role == 'orientation':
                    beat.update(owner=None, mode='summary', witnesses=[])
                guides.append({**base, 'observable': sentence, 'narration': beat})
                steps.append({'beat': len(guides), 'role': role, 'focus_quote': sentence[:4],
                    'bridge_quote': example[i - 1][1][:4] if i else None,
                    'connection': '审稿独见的设计说明，由上一处可见变化带出后续' if i else None,
                    'detail': detail, 'status': 'pending' if role == 'handoff' else 'observed'})
            sequence = {'scene': base['scene'], 'steps': steps}
            if self.kind == 'procedure_branch':
                sequence['comparison'] = {'gate_quote': data['passage_choices'][0]['need_quote'],
                    'example_beat': steps[0]['beat'], 'example_actor': '先到的人', 'example_choice': '签了借条',
                    'branch_beat': steps[2]['beat'], 'branch_actor': '沈砚', 'branch_choice': '把借条推回去'}
            raw['products']['passage_sequences'] = [sequence]
            result.text = json.dumps(raw, ensure_ascii=False)
        elif 'material_review' in data:
            self.reviews += 1
            assert '独立定位' in messages[0]['content']
            assert ('办理分流依据' in messages[0]['content']) == (self.kind == 'procedure_branch')
            assert ('注意力转移核对' in messages[0]['content']) == (self.kind == 'focus_relay')
            raw = json.loads(result.text)
            checks = {r['id']: r for r in data['material_review']['checks']}
            first = next(c for c in checks.values() if 'passage_choice' in c)
            assert '审稿独见' in first['passage_choice']['reason']
            current = data['draft']['text']
            for row in raw['material_checks']:
                check = checks[row['id']]
                if 'passage_step' not in check:
                    continue
                role = check['passage_step']['role']
                sentence = next(s for r, s, _ in example if r == role)
                if self.reviews == 1 and role == example[-1][0]:
                    wrong = WRONG_ENDING[self.kind]
                    start = current.index(wrong)
                    code = 'passage_status' if self.kind == 'procedure_branch' else 'viewpoint'
                    row.update(status='failed', reason=f'[{code}] 审稿员私下判断',
                               evidence=[{**data['material_review']['draft'], 'start': start, 'end': start + len(wrong), 'quote': wrong}])
                    continue
                start = current.index(sentence)
                if self.reviews == 1:
                    start, stop = 0, len(current)
                else:
                    stop = start + len(sentence)
                row['evidence'] = [{**data['material_review']['draft'], 'start': start, 'end': stop,
                                    'quote': current[start:stop]}]
                row['reason'] = f'“{sentence[2:6]}”使本拍的对象及变化可辨。审稿员私下判断'
            result.text = json.dumps(raw, ensure_ascii=False)
        elif 'items' in data or data.get('review'):
            package = data.get('context', data)
            projected = [json.loads(i['text']) for i in package['items'] if i['source'].startswith('material:work:narration:')]
            selected = [json.loads(i['observable'])['passage_step'] for i in projected if 'passage_step' in i['observable']]
            assert [p['role'] for p in selected] == [r for r, _, _ in example]
            if self.kind == 'focus_relay':
                assert selected[1]['from_audience'] == 'reader_only'
            assert '审稿独见' not in messages[-1]['content'] and '审稿员私下判断' not in messages[-1]['content']
            if data.get('review'):
                self.revisions += 1
                feedback = {r.get('fix') for r in data['review']['material_checks']}
                assert FIXES['passage_order'] in feedback
                assert (FIXES['passage_status'] if self.kind == 'procedure_branch' else narration_review.FIXES['viewpoint']) in feedback
            sep = '\n' if self.revisions and self.kind == 'focus_relay' else ''
            sentences = [s for _, s, _ in example]
            if not self.revisions:
                sentences[-1] = WRONG_ENDING[self.kind]
            result.text = '[FAKE] 沈砚走进档案室核验旧印。' + sep.join(sentences)
        elif '{"operations"' in messages[0]['content']:
            limits = data['context']['reader_only_spans']
            if self.kind == 'procedure_branch':
                pending = next(s for s in limits if s.get('passage_status') == 'pending')
                with pytest.raises(ValueError, match='独立凭据'):
                    narration_review.check_state_audience([{'holder': 'WORLD', 'claim': 'fact',
                        'predicate': '封条已取回', 'evidence': [pending]}], limits)
                narration_review.check_state_audience([{'holder': 'READER', 'claim': 'plan',
                    'predicate': '等候取回', 'evidence': [pending]}], limits)
            else:
                orientation = next(s for s in limits if 'holders' not in s)
                with pytest.raises(ValueError, match='仅向读者讲述'):
                    narration_review.check_state_audience([{'holder': 'yan', 'claim': 'belief',
                                                            'evidence': [orientation]}], limits)
            raw = json.loads(result.text)
            for op in raw['operations']:
                op.setdefault('expected_old', None)
                op['evidence'][0]['end'] = data['draft']['text'].index('。') + 1
            result.text = json.dumps(raw, ensure_ascii=False)
        return result


@pytest.mark.parametrize('kind', EXAMPLES)
def test_adopted_passage_reaches_design_draft_revision_acceptance_and_reopen(tmp_path, kind):
    template_catalog(tmp_path)
    folder = tmp_path / 'novel'
    with Store(folder, create=True, test_mode=True) as store:
        store.init_project('[FAKE] 接续叙述写审')
        store.add_brief('在档案室核验被替换的旧封条')
        adopt_story(store, baseline(), {})
        model = PassageModel(kind)
        runtime = replace(config(store), source_driven=True)
        design = start_job(store, JobRequest('design', budget=Budget(42, 140000, 4800))).id
        result = resume_job(store, design, model, runtime)
        assert result.step == 'plan:book:confirm', result.reason
        result = resume_job(store, design, model, runtime, choose)
        assert result.step == 'plan:chapter:confirm', result.reason
        result = resume_job(store, design, model, runtime, choose)
        assert result.status == 'DONE', result.reason
        scene, = store.list('scene')
        writing = start_job(store, JobRequest('write', scene_ids=[scene.id], budget=Budget(16, 140000, 4800, 1))).id
        done = resume_job(store, writing, model, runtime, author())
        assert done.status == 'DONE', done.reason
        assert (model.reviews, model.revisions) == (2, 1)
    with Store(folder, test_mode=True) as reopened:
        selected = reopened.get('draft', reopened.accepted(scene.id).draft_id)
        assert selected.text.endswith(EXAMPLES[kind][-1][1])
        assert WRONG_ENDING[kind] not in selected.text
        from nw.materials.evidence import scene_materials
        visible = writer_checks(scene_materials(reopened, scene.id))
        assert len([r for r in visible if 'passage_step' in r['observable']]) == len(EXAMPLES[kind])


def test_passage_review_checks_actual_rationale_and_global_narration_order(draft):
    cut = draft.text.index('。') + 1
    early, late = span(draft, 0, cut), span(draft, cut, len(draft.text))
    checks = [{'id': 'work:narration:s:1', 'narration_order': 1, 'profile': 'method_work', 'passage_step': {}},
              {'id': 'work:narration:s:2', 'narration_order': 2, 'profile': 'method_work'}]
    rows = [{'id': checks[0]['id'], 'status': 'pass', 'reason': '“缺失的那页”指出究竟找到了什么。', 'evidence': [early, late]},
            {'id': checks[1]['id'], 'status': 'pass', 'reason': '能定位现场的动作', 'evidence': [early]}]
    def evaluate():
        return action_review.review_result(review_run(draft, rows), {'checks': checks}, draft, None)
    assert evaluate()['material_checks'][1]['narration_issue'] == 'passage_order'
    rows[1]['evidence'] = [late]
    assert evaluate()['recommendation'] == 'pass'
    rows[0]['reason'] = '审稿员已经逐项核对了这个位置。'
    assert evaluate()['material_checks'][0]['narration_issue'] == 'passage_evidence'


def test_short_time_cut_and_command_have_their_own_positions_without_inventing_words(draft):
    draft = replace(draft, text='所有人都在台前等着叫号。\n\n一刻钟后。\n\n重来！')
    lead = span(draft, 0, draft.text.index('。') + 1)
    turn = span(draft, draft.text.index('一刻钟'), draft.text.index('后。') + 2)
    order = span(draft, draft.text.index('重来'), len(draft.text))
    checks = [{'id': f'work:narration:s:{i}', 'profile': 'method_work', 'narration_order': i, 'passage_step': {},
               'method_artifact': {'narration': {'owner': None, 'time': 'current'}}} for i in (1, 2)]
    rows = [{'id': check['id'], 'status': 'pass', 'reason': why, 'evidence': [lead, actual]}
            for check, actual, why in zip(checks, (turn, order), ('“一刻钟”跳过等候，轮到下一人。', '“重来”让队列停下。'))]
    result = action_review.review_result(review_run(draft, rows), {'checks': checks}, draft, None)
    assert result['recommendation'] == 'pass'
    seen = narration_review.reader_spans(checks, result['material_checks'], draft)
    assert [(r['start'], r['end']) for r in seen] == [(s['start'], s['end']) for s in (turn, order)]
    rows[1].update(evidence=[lead, turn], reason='“一刻钟”就算作第二拍。')
    assert action_review.review_result(review_run(draft, rows), {'checks': checks}, draft, None)['recommendation'] == 'revise'
