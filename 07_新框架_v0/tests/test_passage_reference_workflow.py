"""An imported reference must affect the current project scene and its independent review."""
from dataclasses import replace
import json

import pytest

from nw.materials.evidence import scene_materials
from nw.novel_flow import JobRequest, resume_job, start_job
from nw.production_methods.passage_sources import recommendations, scene_candidates
from nw.production_methods.selection import verify_sources
from nw.store import Store
from nw.story_state import adopt_story
from nw.studio.library import LibraryService
from nw.studio.production_inputs import freeze_wizard, governance
from nw.task_models import Budget
from story_fixture import baseline
from test_material_phase_flow import template_catalog
from test_material_workflow import choose
from test_novel_flow import author, config
from test_passage_prose import PassageModel
from test_studio_corpus_passages import start_passage_method


def test_fresh_reference_selected_for_current_scene_is_still_verifiable_after_reopening(tmp_path, monkeypatch):
    template_catalog(tmp_path)
    lib = LibraryService(tmp_path)
    wizard = freeze_wizard({'title':'柜前的影子', 'idea':'核对旧封条', 'genre_ids':['GENRE_XUANYI']}, lib)
    assert 'passage_references' not in wizard
    book, _, method = start_passage_method(lib, monkeypatch, 'focus_relay')
    fresh = governance(wizard, library=lib)['world_design']['passage_references']
    ref, = fresh
    assert ref['method_id'] == method['id'] and ref['scopes'] == ['chapter']
    assert not governance(wizard).get('world_design', {}).get('passage_references')
    assert not recommendations(lib, ['GENRE_XUANHUAN'])
    assert not any(s['quote'] in json.dumps(fresh, ensure_ascii=False) for s in method['body']['evidence'])

    class SourceModel(PassageModel):
        def generate(self, messages, **params):
            data = json.loads(messages[-1]['content'])
            result = super().generate(messages, **params)
            stage = data.get('stage')
            if stage in ('scene_design', 'expression_design'):
                products = json.loads(result.text)['products']
                candidate, = data['passage_references']
                assert candidate['ref'] == ref['ref']
                if stage == 'scene_design':
                    choice, = products['passage_choices']
                    assert choice['event'] in candidate['events']
                    choice['source_ref'] = ref['ref']
                    choice['fit'] = {'condition':candidate['condition'], 'boundary':candidate['boundary'],
                                     'prior_quote':choice['need_quote'],
                                     'boundary_check':f"要{choice['need_quote']}，可以跟着正在验印者的眼光到纸角；现场已有可观察的目标。"}
                else:
                    seq, = products['passage_sequences']
                    seq.update(source_operation=candidate['operations'][0], source_beat=seq['steps'][1]['beat'])
                result.text = json.dumps({'stage':stage,'products':products}, ensure_ascii=False)
            if 'material_review' in data:
                check, = [r for r in data['material_review']['checks'] if 'passage_source' in r]
                assert check['passage_source'] == {'ref': ref['ref'], 'operation': ref['operations'][0]}
                assert check['passage_fit']['boundary'] == ref['boundary']
                assert check['passage_limits']['non_applicability'] == method['body']['non_applicability']
            return result

    folder = tmp_path / 'production'
    # The client keeps source materials at the logical workspace and stores novels separately.
    separate = tmp_path / 'novels'
    with Store(folder, create=True, test_mode=True, projects_root=separate) as store:
        store.init_project('[FAKE] 参考方法贯通')
        store.add_brief(wizard['idea'])
        adopt_story(store, baseline(), {})
        model = SourceModel('focus_relay')
        runtime = replace(config(store), source_driven=True)
        design = start_job(store, JobRequest('design', budget=Budget(44, 140000, 4800),
                           governance_inputs={'world_design':{'passage_references':fresh}})).id
        result = resume_job(store, design, model, runtime)
        assert result.step == 'plan:book:confirm', result.reason
        result = resume_job(store, design, model, runtime, choose)
        assert result.step == 'plan:chapter:confirm', result.reason
        result = resume_job(store, design, model, runtime, choose)
        assert result.status == 'DONE', result.reason
        scene, = store.list('scene')
        writing = start_job(store, JobRequest('write', scene_ids=[scene.id], budget=Budget(16, 140000, 4800, 1))).id
        done = resume_job(store, writing, model, runtime, author())
        assert done.status == 'DONE' and model.reviews == 2, done.reason
    with Store(folder, test_mode=True, projects_root=separate) as store:
        saved = scene_materials(store, scene.id)['work_session']
        verify_sources(store, saved)
        lib.review_book(book, {'decision':'reject','note':'隔离试验，撤回来源'})
        assert not governance(wizard, library=lib).get('world_design', {}).get('passage_references')
        with pytest.raises(ValueError, match='STALE_PROJECT_METHOD'):
            verify_sources(store, saved)
        assert store.accepted(scene.id).draft_id


def test_rank_after_real_event_and_action_demands_are_known():
    pool = [{'ref':str(i), 'kind':'procedure_branch', 'condition':condition,
             'operations':[], 'boundary':'', 'roles':[]} for i,condition in enumerate(
             ('入学报到','验收入库','柜前换证与挂失','领药付账'))]
    events = {'a':{'goal':'柜前换证'}, 'b':{'goal':'查问值班人员'}}
    rows = scene_candidates(pool, events, [{'event':'a','action':'受理挂失'}, {'event':'b','action':'领药付账'}])
    selected = {row['ref']: row['events'] for row in rows}
    assert selected['2'] == ['a'] and selected['3'] == ['b']
