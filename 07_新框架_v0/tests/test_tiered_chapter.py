"""Exercise the selected book tier through planning, writing, independent review and acceptance."""
from dataclasses import replace
import json

import pytest

from nw.acceptance import accept_batch
from nw.chapter_break import break_is_natural
from nw.context.story import build_story_context, scene_scope
from nw.length_plan import approved_length_budgets, design_context, validate_direction
from nw.llm.base import GenResult
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.planning import propose_plan
from nw.store import Store
from nw.story_state import adopt_story, current_head, revision_state
from nw.task_models import Budget
from story_fixture import baseline, draft_for, proposal
from test_length_plan import budget, plan
from test_novel_flow import Model, author, config
from test_planning import apply


def tiered_project(store):
    store.init_project('[FAKE] 自然分章')
    store.add_brief('找回丢失的钥匙')
    adopt_story(store, baseline(), {})
    params = {'plot_design': {'length_policy': {'length_mode': 'tiered', 'target_words': 300000}}}
    previous = None
    for scope in ('book', 'chapter'):
        planner = plan(scope, total=300000)
        for candidate in planner.output['candidate_cards']:
            # One hundred chapters is a preliminary estimate. The chapter step may refine it.
            candidate['body']['length_plan']['chapter_count'] = 100 if scope == 'book' else 130
            for member in candidate['members']:
                if member['kind'] == 'chapter':
                    member['body']['word_budget'] = budget(2200, 2000, 2500, '问话结束后留住下一条线索')
                elif member['kind'] == 'scene':
                    member['body']['word_budget'] = budget(500, 480, 520, '人物顺着线索行动')
        result = propose_plan(store, 1, scope, planner, config(store), Budget(1, 60000, 3000),
                              parent_id=previous, governance_inputs=params)
        apply(store, result)
        previous = result.id
    return sorted(store.list('scene'), key=lambda s: s.index)


class ClosingModel(Model):
    def __init__(self, size, last, *, forged=False, failed=False):
        super().__init__()
        self.size, self.last, self.forged, self.failed = size, last, forged, failed

    def generate(self, messages, **params):
        payload = json.loads(messages[-1]['content'])
        if 'items' in payload:
            self.calls.append(messages)
            quote = self.last if any(row['source'] == 'chapter:length' and
                    json.loads(row['text']).get('chapter_end') for row in payload['items']) else '她终于找到了小钥匙。'
            # Both scenes deliberately depart from their optional 480–520 estimate.
            size = self.size - 800 if quote == self.last else 800
            prefix = '[FAKE] '
            text = prefix + '甲' * (size - len(prefix.strip()) - len(quote) - 1) + '。\n' + quote
            return GenResult(text, 'complete', {}, 'test', {})
        if 'draft' in payload and '章末状态：' in messages[0]['content']:
            self.calls.append(messages)
            verdict = {'status': 'revise' if self.failed else 'natural', 'quote': '并非本稿的最后一句。' if self.forged else self.last,
                       'reason': '最后一个动作落定，本章的问话在人物离开时收束。'}
            notes = ('已核对末段。\n章末状态：' + verdict['status'] + '\n章末引句：' + verdict['quote'] +
                     '\n章末理由：' + verdict['reason'])
            return GenResult(json.dumps({'recommendation':'pass', 'core_changes':[], 'notes':notes},
                                        ensure_ascii=False), 'complete', {}, 'test', {})
        return super().generate(messages, **params)


@pytest.mark.parametrize('size,forged,failed', [(2000, False, False), (2500, False, False), (2173, False, False),
                                                (1999, False, False), (2501, False, False), (2150, True, False),
                                                (2150, False, True)])
def test_chapter_interval_and_real_final_paragraph(tmp_path, size, forged, failed):
    with Store(tmp_path / 'books', create=True, test_mode=True) as store:
        first, last = tiered_project(store)
        state = revision_state(store, current_head(store))
        budgets = approved_length_budgets(store, state)
        assert budgets['tiered_scenes'] == {first.id, last.id}
        ctx = build_story_context(store, last.id, scene_scope(store, last.id), 64000)
        assert '完整段落' in ctx.prompt
        model = ClosingModel(size, '她合上旧案卷，带着那把钥匙走出门。', forged=forged, failed=failed)
        job = start_job(store, JobRequest('write', scene_ids=[first.id, last.id], budget=Budget(20, 64000, 4000, 0)))
        result = resume_job(store, job.id, model, config(store), author())
        if size < 2000 or size > 2500:
            assert result.status == 'BLOCKED' and '整章实际' in result.reason
        elif failed or forged:
            assert result.status == 'BLOCKED' and '章末' in result.reason, result.reason
        else:
            assert result.status == 'DONE', result.reason
            assert len(store.list('accepted')) == 2
        from nw.studio.production_views import ProductionViews
        displayed = ProductionViews.review_for_draft(store, last.id, store.drafts(last.id)[-1].id)['result']
        if result.status != 'DONE':
            assert not store.list('accepted')
            assert displayed['recommendation'] in ('invalid', 'revise')
        else:
            assert displayed['recommendation'] == 'pass' and displayed['chapter_break']['status'] == 'natural'


def test_manually_forcing_in_range_ending_requires_review_on_that_version(tmp_path):
    with Store(tmp_path / 'manual', create=True, test_mode=True) as store:
        first, last = tiered_project(store)
        head = current_head(store)
        prior = draft_for(store, first.id, '甲' * 900)
        head = accept_batch(store, [proposal(store, head, prior, [])], head, 'first')
        brief = {'text':'选择项目篇幅\n\n立项参数：\n{"length_mode":"tiered","target_words":300000}'}
        context = design_context(store, brief, revision_state(store, head), None)
        assert (context['accepted_words'], context['pending_planned_words'], context['pending_max_words']) == (900, 1300, 1600)
        assert (context['book_min_words'], context['book_max_words']) == (200000, 399999)
        draft = draft_for(store, last.id, '乙' * 1100 + '。')
        with pytest.raises(ValueError, match='本版正文对应的自然断章审稿'):
            accept_batch(store, [proposal(store, head, draft, [])], head, 'without-independent-review')
        partial = replace(draft, text='灯没有熄。\n她没能说完那句话，')
        assert not break_is_natural({'status':'natural','quote':'她没能说完那句话，', 'reason':'打算留悬念'}, partial)


def test_tiered_book_and_chapter_with_source_steps_and_material_review(tmp_path):
    from test_material_phase_flow import PhaseModel, template_catalog
    from test_material_stage_roundtrip import StageModel
    from test_material_workflow import choose
    ending = '他将查过的案卷还了回去。'

    class SourceModel(PhaseModel, StageModel):
        def generate(self, messages, **params):
            result = super().generate(messages, **params)
            payload = json.loads(messages[-1]['content'])
            prompt = messages[0]['content']
            if '[MATERIAL_STEP]' in prompt and 'length_context' in payload:
                data = json.loads(result.text)
                for item in data['products'].get('directions', ()):
                    item['length_plan'] = {'target_words': 300000, 'chapter_count': 140, 'reason': '案情多次变化'}
                for item in data['products'].get('members', ()):
                    if item['kind'] == 'chapter':
                        item['body']['word_budget'] = budget(2200, 2000, 2500, '验印完毕后归还案卷')
                    elif item['kind'] == 'scene':
                        item['body']['word_budget'] = budget(1500, 1400, 1600, '动作粗估')
                result.text = json.dumps(data, ensure_ascii=False)
            elif 'items' in payload:
                result.text = result.text + '甲' * 1980 + '。\n' + ending
            elif '章末状态：' in prompt:
                data = json.loads(result.text)
                assert payload['material_review']['checks']
                data['notes'] += '\n章末状态：natural\n章末引句：' + ending + '\n章末理由：归还案卷完成了本章任务'
                result.text = json.dumps(data, ensure_ascii=False)
            elif '{"operations"' in prompt:
                data = json.loads(result.text)
                for op in data['operations']:
                    op.setdefault('expected_old', None)
                result.text = json.dumps(data, ensure_ascii=False)
            return result

    template_catalog(tmp_path)
    with Store(tmp_path / 'staged', create=True, test_mode=True) as store:
        store.init_project('[FAKE] 类型篇幅与原始资料合验')
        store.add_brief('入井查封条')
        adopt_story(store, baseline(), {})
        model = SourceModel('fixture')
        runtime = replace(config(store), source_driven=True)
        prefs = {'plot_design': {'length_policy': {'length_mode':'tiered'}, 'length_auto': True}}
        request = JobRequest('design', budget=Budget(40, 120000, 4000), governance_inputs=prefs)
        job = start_job(store, request).id
        assert resume_job(store, job, model, runtime).step == 'plan:book:confirm'
        assert resume_job(store, job, model, runtime, choose).step == 'plan:chapter:confirm'
        outcome = resume_job(store, job, model, runtime, choose)
        assert outcome.status == 'DONE', outcome.reason
        scene, = store.list('scene')
        writer = start_job(store, JobRequest('write', scene_ids=[scene.id], budget=Budget(12, 120000, 4000, 0))).id
        accepted = resume_job(store, writer, model, runtime, author())
        assert accepted.status == 'DONE', accepted.reason
        assert store.accepted(scene.id)


def test_ai_selects_one_available_tier_without_inheriting_a_legacy_custom_target(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        store.init_project('[FAKE] 档位切换')
        brief = {'text':'重新设计篇幅\n\n立项参数：\n{"length_mode":"tiered"}'}
        legacy = {'body':{'length_plan':{'target_words':160000,'chapter_count':80,'reason':'旧要求'}}}
        context = design_context(store, brief, None, legacy)
        assert not context['parent_plan']
        assert len(context['book_tiers']) == 5
        plan = {'length_plan':{'chapter_count':120,'target_words':300000,'reason':'调查与追踪的体量'}}
        validate_direction(plan, context)
        plan['length_plan']['target_words'] = 370000
        with pytest.raises(ValueError, match='全书篇幅'):
            validate_direction(plan, context)
        context['policy']['target_words'] = 500000
        plan['length_plan']['target_words'] = 300000
        with pytest.raises(ValueError, match='当前档位'):
            validate_direction(plan, context)

def test_review_revises_an_in_range_chapter_with_an_unfinished_paragraph(tmp_path):
    unfinished = '她把案卷放下，刚刚想再说，'
    complete = '她合上案卷，目送证人走出门。'

    class ParagraphRevision(ClosingModel):
        def generate(self, messages, **params):
            payload = json.loads(messages[-1]['content'])
            if 'draft' in payload and 'review' in payload:
                self.calls.append(messages)
                assert payload['chapter_break_revision']
                return GenResult(payload['draft']['text'].removesuffix(unfinished) + complete,
                                 'complete', {}, 'test', {})
            if '章末状态：' in messages[0]['content']:
                self.last = payload['draft']['text'].splitlines()[-1]
            return super().generate(messages, **params)

    with Store(tmp_path / 'rewrite', create=True, test_mode=True) as store:
        scenes = tiered_project(store)
        model = ParagraphRevision(2200, unfinished)
        request = JobRequest('write', scene_ids=[sc.id for sc in scenes], budget=Budget(20, 64000, 4000, 1))
        job = start_job(store, request).id
        result = resume_job(store, job, model, config(store), author())
        assert result.status == 'DONE', result.reason
        original, revised = store.drafts(scenes[-1].id)
        assert original.text.endswith(unfinished) and revised.text.endswith(complete)
        assert store.accepted(scenes[-1].id).draft_id == revised.id
