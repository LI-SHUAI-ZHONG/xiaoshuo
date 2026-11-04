
import json
from dataclasses import asdict

import pytest

from nw.cards import decide_card
from nw.context.story import StoryScope, build_story_context
from nw.generation import review_draft, write_scene
from nw.llm.fake import FakeProvider
from nw.store import Store
from nw.story_models import StateHead
from nw.story_state import adopt_story
from nw.task_models import Budget
from nw.tasks import read_input_manifest
from story_fixture import baseline, draft_for, operation, proposal, seed_book
from test_selection import add_card


@pytest.fixture
def project(tmp_path):
    with Store(tmp_path, create=True, test_mode=True) as store:
        [scene] = seed_book(store, 1)
        store.add_brief('调查暗井', '禁止改动结局')
        approvals = []
        for ident, kind, body in [
            ('yan', 'character', {'name': '沈砚', 'role': '主角', 'want': '查封条', 'visibility': 'public'}),
            ('other', 'character', {'name': '沈', 'role': '路人', 'want': 'OTHER_NAME', 'visibility': 'public'}),
            ('secret', 'world', {'title': '隐藏', 'rule': 'SECRET_RULE', 'limits': '保密'}),
            ('scene-card', 'scene', {'title': '暗井', 'goal': '沈砚调查证物，面对权力不对称', 'pov': 'yan',
                                     'characters': ['yan'], 'story_time': '1', 'visibility': 'public'}),
        ]:
            ref = add_card(store, ident, kind, body)
            approval = decide_card(store, ref, 'approved', '已确认')
            approvals.append({**asdict(ref), 'decision_id': approval.id})
        facts = [{'entity_id': 'well', 'predicate': 'password', 'holder': holder, 'claim': claim,
                  'value': value, 'story_order': 0, 'disclosure_order': [0, 0, 0]}
                 for holder, claim, value in [('WORLD', 'fact', 'SECRET_FACT'),
                                              ('yan', 'belief', 'POV_BELIEF')]]
        facts.extend({'entity_id': 'well', 'predicate': key, 'holder': holder, 'claim': 'fact',
                      'value': value, 'story_order': 0, 'disclosure_order': [0, 0, 0]}
                     for key, holder, value in [('secret', 'READER', 'READER_ONLY'),
                                                ('location', 'yan', 'SHARED_FACT'),
                                                ('location', 'READER', 'SHARED_FACT')])
        adopt_story(store, baseline(card_refs=approvals, facts=facts), {})
        yield store, scene.id, StoryScope('main', 0, 1, {'card_id': 'scene-card', 'version': 1})


def test_secret_not_in_pov_package(project):
    context = json.dumps(build_story_context(*project, 10000).package, ensure_ascii=False)
    assert 'POV_BELIEF' in context
    assert 'SECRET_FACT' not in context and 'SECRET_RULE' not in context and 'READER_ONLY' not in context
    assert 'belief' in context
    package = build_story_context(*project, 10000).package
    reader = next(item for item in package['items'] if item['source'] == 'reader')
    assert json.loads(reader['text'])[0]['value'] == 'SHARED_FACT'


def test_hard_constraints_not_silently_truncated(project):
    with pytest.raises(ValueError, match='CONTEXT_TOO_LARGE'):
        build_story_context(*project, 30)


def test_scene_links_use_ids_not_name_substrings(project):
    context = json.dumps(build_story_context(*project, 10000).package, ensure_ascii=False)
    assert '沈砚' in context and 'OTHER_NAME' not in context


def test_restore_uses_frozen_source_version(project):
    store, scene, scope = project
    from nw.sources import import_seed_cards, read_span
    from nw.story_models import SourceRef
    from test_cards import MANIFEST, ROOT

    refs = import_seed_cards(store, MANIFEST, root=ROOT)
    rule = next(ref for ref in refs if ref.card_id == 'rule-5.6')
    decide_card(store, rule, 'trial', '按场景试用真实来源')
    budget = Budget(2, 12000, 120)
    provider = FakeProvider()
    run, draft = write_scene(store, scene, provider, 'test', {}, story_scope=scope, budget=budget)
    manifest_id = json.loads(run.input_snapshot_json)['manifest_id']
    frozen, package = read_input_manifest(store, manifest_id)
    decide_card(store, rule, 'disabled', '撤回试用')
    assert asdict(rule) in frozen['card_refs']
    assert frozen['source_refs']
    assert all(read_span(store, SourceRef(**raw)) for raw in frozen['source_refs'])
    assert read_input_manifest(store, manifest_id) == (frozen, package)
    reviewed = review_draft(store, draft.id, provider, 'test', {}, budget=budget)
    assert json.loads(reviewed.context_package_json) == package
    reviewed_manifest, _ = read_input_manifest(store, json.loads(reviewed.input_snapshot_json)['manifest_id'])
    assert any(ref['kind'] == 'draft' and ref['id'] == draft.id for ref in reviewed_manifest['dependency_refs'])


def test_managed_write_uses_story_context(project):
    store, scene, scope = project
    provider = FakeProvider()
    run, draft = write_scene(store, scene, provider, 'test', {}, story_scope=scope,
                             budget=Budget(1, 12000, 120))
    assert draft is not None and draft.text.startswith('[FAKE]')
    manifest_id = json.loads(run.input_snapshot_json)['manifest_id']
    frozen, package = read_input_manifest(store, manifest_id)
    assert (frozen['branch_id'], frozen['state_revision'], frozen['story_order']) == ('main', 0, 1)
    assert json.loads(provider.calls[0][-1]['content']) == package
    assert store.connection.execute(
        "SELECT COUNT(*) FROM artifact_dependencies WHERE consumer_kind='run' AND consumer_id=?",
        (run.id,)).fetchone()[0] >= 3


def test_pov_knowledge_disclosed_later_keeps_the_draft_dependency(project):
    from dataclasses import replace

    from nw.acceptance import accept_batch
    from nw.story_delta import draft_ref

    store, earlier, scope = project
    chapter = store.get('scene', earlier).chapter_id
    later = store.add_scene(chapter, 2, '{}')
    draft = draft_for(store, later.id)
    head = StateHead('main', 0)
    request = proposal(store, head, draft, [
        operation(draft, time=0, order=(1, 2, 0), holder='yan', claim='belief',
                  entity='well', predicate='password', old='POV_BELIEF', new='FROM_LATER_SCENE'),
    ])
    accepted = accept_batch(store, [request], head, 'later')
    work = build_story_context(store, earlier, replace(scope, revision=accepted.revision), 15000)
    assert 'FROM_LATER_SCENE' in json.dumps(work.package)
    assert draft_ref(draft) in work.dependency_refs
    assert not work.predecessor_drafts
