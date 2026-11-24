
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


def test_previous_chapter_flash_forward_is_not_raw_pov_context(project):
    from nw.acceptance import accept_batch
    from nw.story_delta import draft_ref

    store, earlier, scope = project
    chapter = store.add_chapter(2, '当时')
    scene = store.add_scene(chapter.id, 1, '{}')
    binding = {'story': {'scene_ref': scope.scene_ref, 'story_order': 9}}
    store.connection.execute('UPDATE scenes SET card_json=? WHERE id=?', (json.dumps(binding), earlier))
    future = 'FUTURE_SCENE_PASSCODE'
    draft = draft_for(store, earlier, f'沈砚在井口听到了{future}。')
    head = StateHead('main', 0)
    request = proposal(store, head, draft, [operation(draft, time=9, holder='yan', claim='belief',
        entity='well', predicate='password', old='POV_BELIEF', new=future)])
    accepted = accept_batch(store, [request], head, 'earlier chapter')
    work = build_story_context(store, scene.id, StoryScope('main', accepted.revision, 1, scope.scene_ref), 15000)
    assert future not in json.dumps(work.package)
    assert not any(item['source'].startswith('previous:') for item in work.package['items'])
    assert draft_ref(draft) in work.predecessor_drafts


def test_scene_design_uses_character_history_and_separate_reader_clock(project):
    from nw.acceptance import accept_batch
    from nw.materials import scene_knowledge
    from nw.materials.narration import EVIDENCE_POLICY, scene_bases

    store, first, _ = project
    last = store.add_scene(store.add_chapter(3, '晚揭示').id, 1, '{}')
    later_draft = draft_for(store, first, '未来才会改变的判断。')
    old_draft = draft_for(store, last.id, '回溯得知的信息。')
    head = StateHead('main', 0)
    head = accept_batch(store, [proposal(store, head, later_draft, [
        operation(later_draft, time=8, holder='yan', claim='belief', entity='well', predicate='password',
                  old='POV_BELIEF', new='FUTURE_BELIEF'),
        operation(later_draft, time=8, holder='READER', entity='well', predicate='seal', new='READER_FLASH_FORWARD'),
    ])], head, 'future')
    head = accept_batch(store, [proposal(store, head, old_draft, [
        operation(old_draft, time=2, order=(3, 1, 0), holder='yan', entity='well', predicate='location',
                  old='SHARED_FACT', new='EARLIER_CHARACTER_KNOWLEDGE'),
        operation(old_draft, time=2, order=(3, 1, 0), holder='READER', entity='well', predicate='location',
                  old='SHARED_FACT', new='LATER_READER_REVEAL'),
        operation(old_draft, time=2, order=(3, 1, 0), holder='yan', entity='other', predicate='identity',
                  new='先前在簿册核实了他是来接手的掌柜'),
    ])], head, 'flashback')
    scenes = {'chapters': [{'index': 2, 'scenes': [{'index': 1, 'story_order': 3, 'card': 's'}]}],
              'members': [{'key': 's', 'body': {'pov': 'yan', 'characters': ['yan', 'other']}}]}
    frozen = scene_knowledge.freeze(store, asdict(head), scenes)
    products = {'scene_design': {'products': scenes}}
    cards = [{'card_id': 'yan', 'kind': 'character', 'body': {'name': '沈砚', 'visibility': 'public'}},
             {'card_id': 'other', 'kind': 'character', 'body': {'name': '掌柜', 'visibility': 'public', 'casting': {
                 'entry': 'other', 'public_identity': '掌柜', 'introducer': 'yan',
                 'introducer_source': 'prior', 'introducer_basis': '在簿册核实'}}}]
    context = {'scene_knowledge_policy': scene_knowledge.POLICY, 'narration_scene_facts': frozen,
               'narration_policy': EVIDENCE_POLICY, 'approved_cards': cards}
    bases = scene_bases(products, context)['s']
    texts = {source['text'] for source in bases.values() if source['kind'] == 'state'}
    assert {'POV_BELIEF', 'EARLIER_CHARACTER_KNOWLEDGE', 'SHARED_FACT'} <= texts
    assert {'FUTURE_BELIEF', 'LATER_READER_REVEAL', 'SECRET_FACT', 'READER_FLASH_FORWARD'}.isdisjoint(texts)
    assert bases['cast:other:entry']['state_sha256']
    with pytest.raises(ValueError, match='scene knowledge'):
        scene_bases(products, {**context, 'narration_scene_facts': {}})
    package = {'scene_knowledge_policy': scene_knowledge.POLICY, 'branch_head': asdict(head)}
    session = {'stages': [{'stage': 'scene_design', 'products': scenes}], 'context': context}
    scene_knowledge.verify_archive(store, package, session)
    with pytest.raises(ValueError, match='scene knowledge'):
        scene_knowledge.verify_archive(store, package, {**session, 'context': {**context, 'narration_scene_facts': {'s': []}}})
