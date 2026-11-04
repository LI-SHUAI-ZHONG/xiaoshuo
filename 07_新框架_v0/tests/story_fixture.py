from dataclasses import asdict
from hashlib import sha256
from uuid import uuid4

from nw.models import Run
from nw.store import Store, now


def seed_book(store: Store, count: int = 2):
    store.init_project('测试')
    chapter = store.add_chapter(1, '章')
    return [store.add_scene(chapter.id, i + 1, '{}') for i in range(count)]


def draft_for(store: Store, scene_id: str, text: str = '沈砚把钥匙交给陆昭。'):
    run = store.add_run(Run(uuid4().hex, scene_id, 'write', 'ollama', 'test', '{}', '{}',
                            '{}', text, 'complete', '{}', now(), now()))
    return store.add_draft(scene_id, text, 'complete', run.id)


def baseline(**overrides):
    return {'as_of_story_order': 0, 'disclosure_order': [0, 0, 0],
            'coverage': {'entities': [], 'predicates': []}, 'facts': [], 'card_refs': [],
            **overrides}


def operation(draft, *, time=1, order=(1, 1, 0), holder='WORLD', claim='fact',
              predicate='owner', old=None, new='陆昭', entity='key'):
    return {'op': 'set', 'entity_id': entity, 'predicate': predicate, 'holder': holder,
            'claim': claim, 'story_order': time, 'disclosure_order': list(order),
            'expected_old': old, 'new_value': new,
            'evidence': [{'draft_id': draft.id, 'text_sha256': sha256(draft.text.encode()).hexdigest(),
                          'start': 0, 'end': len(draft.text)}]}


def proposal(store, head, draft, operations, *, dependencies=(), predecessors=(), ident=None, brief_ref=None):
    from nw.acceptance import record_story_decision
    from nw.story_delta import candidate_projection_digest, save_delta
    from nw.story_models import AcceptanceRequest
    from nw.task_models import InputManifest, content_sha256
    from nw.tasks import freeze_manifest

    scene = store.get('scene', draft.scene_id)
    chapter = store.get('chapter', scene.chapter_id)
    package = {'draft_id': draft.id}
    manifest = InputManifest(id=uuid4().hex, purpose='state_extract',
        settings={'provider':'author','model':'manual','params':{},'prompt_version':'test',
                  'base_url':None,'timeout':None,'stream':False},
        context_sha256=content_sha256(package), branch_id=head.branch_id, state_revision=head.revision,
        story_order=min((op['story_order'] for op in operations), default=1), brief_ref=brief_ref,
        disclosure_order=(chapter.index, scene.index, 0),
        candidate_delta_refs=tuple(dependencies), predecessor_drafts=tuple(predecessors),
        candidate_projection_sha256=candidate_projection_digest(store, head, dependencies, draft.scene_id) if dependencies else None)
    freeze_manifest(store, manifest, package)
    delta = save_delta(store, ident or uuid4().hex, draft.id, manifest.id, operations)
    fields = {'branch_id': head.branch_id, 'scene_id': draft.scene_id, 'draft_id': draft.id,
              'delta_id': delta.id, 'manifest_id': manifest.id}
    decision = record_story_decision(store, 'accept', fields, '核对本稿与段落证据')
    return AcceptanceRequest(**fields, decision_id=decision)
