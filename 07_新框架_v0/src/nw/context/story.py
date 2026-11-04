
"""Scene work packages from explicit card and branch versions."""
from dataclasses import asdict, dataclass
import json

from nw.cards import card_input_ref, read_card, read_links
from nw.context.base import ContextItem, ContextPackage, package
from nw.selection import select_rules
from nw.sources import read_span
from nw.store import Store
from nw.story_delta import draft_ref
from nw.story_dependencies import check_inputs_current, legacy_ref
from nw.story_models import CardRef, Fact, SourceRef, StateHead
from nw.story_state import baseline_for, current_head, position, revision_state, state_at
from nw.task_models import Ref, canonical

WRITE_PROMPT = ('按作者约束和本场任务写正文。仅用POV可知的信息。人物的belief可能有误，'
                '按场景卡的披露边界写作，计划结果仍是候选。方法卡只在适用条件有依据时使用。只输出正文。')


@dataclass(frozen=True)
class StoryScope:
    branch_id: str
    revision: int
    story_order: int
    scene_ref: dict


@dataclass(frozen=True)
class StoryWork:
    scope: StoryScope
    disclosure: tuple[int, int, int]
    package: dict
    brief_ref: Ref | None
    card_refs: tuple[dict, ...]
    source_refs: tuple[dict, ...]
    predecessor_drafts: tuple[Ref, ...]
    dependency_refs: tuple[Ref, ...]
    selection: dict


class StoryProvider:
    name = 'story'

    def build(self, project: dict, scene: dict) -> ContextPackage:
        items = []
        if project['brief'] is not None:
            items.append(ContextItem('brief', canonical(project['brief']), '作者需求与硬约束'))
        items.append(ContextItem('scene:' + scene['card_id'], canonical(scene['body']), '本场任务'))
        for card in project['settings']:
            items.append(ContextItem('card:' + card['card_id'], canonical(card['body']), '本场确认设定'))
        items.append(ContextItem('pov:' + project['holder'], canonical(project['facts']), '此时POV所知与误信'))
        if project.get('continuity'):
            items.append(ContextItem('prior-evidence', canonical(project['continuity']),
                                     '前文中支持本场人物所知的段落定位'))
        if project.get('reader'):
            items.append(ContextItem('reader', canonical(project['reader']),
                                     '读者此前也已得知的本场可用信息'))
        for mapping in project.get('mappings', []):
            items.append(ContextItem('rule:' + mapping['ref']['card_id'], canonical(mapping), '场景问题与写法检验'))
        return package(items)


def _ref(raw: dict) -> CardRef:
    try:
        return CardRef(**raw)
    except TypeError as exc:
        raise ValueError('Expected a versioned scene CardRef') from exc


def scene_scope(store: Store, scene_id: str, branch: str = 'main') -> StoryScope:
    scene = store.get('scene', scene_id)
    binding = json.loads(scene.card_json).get('story')
    if not isinstance(binding, dict) or set(binding) != {'scene_ref', 'story_order'}:
        raise ValueError('CONTEXT_PROVIDER_REQUIRED: provide an approved scene CardRef and story time')
    head = current_head(store, branch)
    return StoryScope(branch, head.revision, binding['story_order'], binding['scene_ref'])


def _check_scene(scene: dict, ref: CardRef, scope: StoryScope, snapshot: dict) -> None:
    selected = {(row['card_id'], row['version']) for row in snapshot['settings']}
    if scene['kind'] != 'scene' or (ref.card_id, ref.version) not in selected:
        raise ValueError('CONTEXT_PROVIDER_REQUIRED: scene version must be approved on this branch')
    if scene['body'].get('story_time') not in (None, str(scope.story_order)):
        raise ValueError('Scene card story time does not match the work package')
    if scene['body'].get('unknowns'):
        raise ValueError('OPEN_DESIGN_QUESTIONS: ' + '；'.join(scene['body']['unknowns']))
    if scene['body']['pov'] in ('AUTHOR', 'WORLD', 'READER'):
        raise ValueError('Scene POV requires a character ID')


def _settings(store: Store, scene: dict, ref: CardRef, visible: list[dict]) -> list[dict]:
    body = scene['body']
    people = {body['pov'], *body.get('characters', [])}
    cards = {(c['card_id'], c['version']): c for c in visible}
    pending = [ref]
    mandatory = set()
    while pending:
        for link in read_links(store, pending.pop()):
            target = (link.target.card_id, link.target.version)
            if link.relation != 'depends_on' or target in mandatory:
                continue
            if target not in cards:
                raise ValueError('MISSING_MANDATORY_INPUT: a required card is unavailable to this POV or branch')
            mandatory.add(target)
            pending.append(link.target)
    if people - {c['card_id'] for c in visible if c['kind'] == 'character'}:
        raise ValueError('MISSING_MANDATORY_INPUT: a scene character ID is unavailable')
    result = [c for key, c in sorted(cards.items())
              if key in mandatory or c['kind'] in ('world', 'style', 'taboo') or c['card_id'] in people]
    if any(card['body'].get('unknowns') and
           (card['kind'] in ('world', 'taboo') or (card['card_id'], card['version']) in mandatory) for card in result):
        raise ValueError('OPEN_DESIGN_QUESTIONS: a mandatory story card has unresolved fields')
    return result


def _previous_refs(store: Store, snapshot: dict, facts: list[Fact],
                   disclosure: tuple[int, int, int]) -> tuple[tuple[Ref, ...], tuple[Ref, ...]]:
    """Pin adjacent prose and all fact evidence, including earlier events disclosed later."""
    earlier = []
    evidence_ids = {item['draft_id'] for fact in facts for item in fact.evidence if 'draft_id' in item}
    for scene_id, slot in snapshot['slots'].items():
        scene = store.get('scene', scene_id)
        order = (store.get('chapter', scene.chapter_id).index, scene.index)
        if order < disclosure[:2]:
            earlier.append((order, slot['draft_id']))
    previous_ids = {ident for _, ident in earlier if ident in evidence_ids}
    if earlier:
        previous_ids.add(max(earlier)[1])
    predecessors = tuple(draft_ref(store.get('draft', ident)) for ident in sorted(previous_ids))
    other_evidence = tuple(draft_ref(store.get('draft', ident)) for ident in sorted(evidence_ids - previous_ids))
    return predecessors, other_evidence


def build_story_context(store: Store, scene_id: str, scope: StoryScope, char_limit: int) -> StoryWork:
    """Freeze the same versioned information the model receives, with source receipts."""
    if type(char_limit) is not int or char_limit < 1:
        raise ValueError('Context character limit must be a positive integer')
    scene = store.get('scene', scene_id)
    chapter = store.get('chapter', scene.chapter_id)
    disclosure = position((chapter.index, scene.index, 0))
    binding = json.loads(scene.card_json).get('story')
    if binding is not None and binding != {'scene_ref': scope.scene_ref, 'story_order': scope.story_order}:
        raise ValueError('Story scope does not match the materialized scene')
    scene_ref = _ref(scope.scene_ref)
    card = read_card(store, scene_ref)
    snapshot = revision_state(store, StateHead(scope.branch_id, scope.revision))
    if scene.id in snapshot.get('stale_plan_scenes', []):
        raise ValueError('STALE_PLAN: this scene was retired by a revised plan on this branch')
    _check_scene(card, scene_ref, scope, snapshot)
    view = state_at(store, scope.branch_id, scope.revision, scope.story_order, card['body']['pov'],
                    disclosure, before_scene=scene_id)
    visible_ids = {c['card_id'] for c in view.settings}
    if any(ref['card_id'] not in visible_ids and read_card(store, CardRef(ref['card_id'], ref['version']))['kind'] == 'taboo'
           for ref in snapshot['settings']):
        raise ValueError('MISSING_MANDATORY_INPUT: an approved taboo is unavailable to this POV')
    settings = _settings(store, card, scene_ref, view.settings)
    briefs = store.briefs()
    brief = briefs[-1] if briefs else None
    facts = [{key: value for key, value in asdict(f).items() if key != 'evidence'} for f in view.facts]
    inputs = {'brief': asdict(brief) if brief else None, 'settings': settings, 'holder': view.holder, 'facts': facts}
    from nw.context.registry import get_provider

    provider = get_provider('story')
    assembled = asdict(provider.build(inputs, card))
    if len(WRITE_PROMPT) + len(canonical(assembled)) > char_limit:
        raise ValueError('CONTEXT_TOO_LARGE: mandatory story inputs exceed the budget')
    predecessors, other_evidence = _previous_refs(store, snapshot, view.facts, disclosure)
    earlier = {ref.id for ref in predecessors}
    continuity = [{'entity_id': fact.entity_id, 'predicate': fact.predicate,
                   'spans': [item for item in fact.evidence if item.get('draft_id') in earlier]}
                  for fact in view.facts if any(item.get('draft_id') in earlier for item in fact.evidence)]
    shared = []
    if disclosure > position(baseline_for(store, scope.branch_id)['disclosure_order']):
        reader = state_at(store, scope.branch_id, scope.revision, scope.story_order, 'READER', disclosure,
                          before_scene=scene_id)
        known = {(fact.entity_id, fact.predicate, canonical(fact.value)) for fact in view.facts if fact.claim == 'fact'}
        shared = [fact for fact in reader.facts if fact.claim == 'fact' and fact.disclosure_order < disclosure
                  and (fact.entity_id, fact.predicate, canonical(fact.value)) in known]
    already_disclosed = [{'entity_id': fact.entity_id, 'predicate': fact.predicate, 'value': fact.value}
                         for fact in shared]
    for name, optional in [('continuity', continuity), ('reader', already_disclosed)]:
        trial = asdict(provider.build({**inputs, name: optional}, card))
        if len(WRITE_PROMPT) + len(canonical(trial)) <= char_limit:
            inputs[name] = optional
            assembled = trial
    if inputs.get('reader'):
        predecessors, other_evidence = _previous_refs(store, snapshot, [*view.facts, *shared], disclosure)
    selection = select_rules(store, scene_ref, view)
    selected = []
    for mapping in selection.mappings:
        trial = asdict(provider.build({**inputs, 'mappings': [*selected, mapping]}, card))
        if len(WRITE_PROMPT) + len(canonical(trial)) > char_limit:
            selection.excluded_reasons.append({'ref': mapping['ref'], 'reason': 'OPTIONAL_CONTEXT_BUDGET'})
        else:
            selected.append(mapping)
            assembled = trial
    selection.mappings = selected
    selection.selected_refs = [_ref(m['ref']) for m in selected]
    cards = [card, *settings, *(read_card(store, _ref(m['ref'])) for m in selected)]
    receipts = {}
    for item in cards:
        for raw in item['source_refs']:
            source = SourceRef(**raw)
            read_span(store, source)
            receipts[source] = raw
    # Keep audit data outside the model-visible package so omissions cannot leak context.
    refs = tuple(dict.fromkeys(card_input_ref(item) for item in cards))
    check_inputs_current(store, list(refs))
    return StoryWork(scope, disclosure, assembled,
                     legacy_ref('brief', store.project().id, brief) if brief else None,
                     tuple({'card_id': ref.id, 'version': ref.version} for ref in refs),
                     tuple(receipts.values()), predecessors, (*refs, *other_evidence), asdict(selection))
